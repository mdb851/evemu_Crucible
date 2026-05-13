/*
    ------------------------------------------------------------------------------------
    LICENSE:
    ------------------------------------------------------------------------------------
    This file is part of EVEmu: EVE Online Server Emulator
    Copyright 2006 - 2021 The EVEmu Team
    For the latest information visit https://evemu.dev
    ------------------------------------------------------------------------------------
    This program is free software; you can redistribute it and/or modify it under
    the terms of the GNU Lesser General Public License as published by the Free Software
    Foundation; either version 2 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License along with
    this program; if not, write to the Free Software Foundation, Inc., 59 Temple
    Place - Suite 330, Boston, MA 02111-1307, USA, or go to
    http://www.gnu.org/copyleft/lesser.txt.
    ------------------------------------------------------------------------------------
    Author:         Captnoord
    Rewrite:        Allan
    Implementation: AlTahir
*/

#include <boost/algorithm/string/replace.hpp>
#include <algorithm>    // Added to prevent std::find from freaking out
#include <exception>
#include <vector>
#include "eve-server.h"


#include "contract/ContractProxy.h"
#include "station/Station.h"
#include "inventory/Inventory.h"
#include "system/SolarSystem.h"

#include "contract/ContractUtils.h"
#include "account/AccountService.h"
#include "account/AccountDB.h"
#include "EVE_Wallet.h"

namespace {

bool CorpWalletKeyToHangarFlag(int32 walletDivKey, EVEItemFlags& outFlag)
{
    switch (walletDivKey) {
        case Account::KeyType::Cash:  outFlag = flagHangar; break;
        case Account::KeyType::Cash2: outFlag = flagCorpHangar2; break;
        case Account::KeyType::Cash3: outFlag = flagCorpHangar3; break;
        case Account::KeyType::Cash4: outFlag = flagCorpHangar4; break;
        case Account::KeyType::Cash5: outFlag = flagCorpHangar5; break;
        case Account::KeyType::Cash6: outFlag = flagCorpHangar6; break;
        case Account::KeyType::Cash7: outFlag = flagCorpHangar7; break;
        default: return false;
    }
    return true;
}

bool CorpHangarTakeAllowed(Client* client, EVEItemFlags fl)
{
    const int64 roles = client->GetCorpRole();
    switch (fl) {
        case flagHangar: return (roles & Corp::Role::HangarCanTake1) != 0;
        case flagCorpHangar2: return (roles & Corp::Role::HangarCanTake2) != 0;
        case flagCorpHangar3: return (roles & Corp::Role::HangarCanTake3) != 0;
        case flagCorpHangar4: return (roles & Corp::Role::HangarCanTake4) != 0;
        case flagCorpHangar5: return (roles & Corp::Role::HangarCanTake5) != 0;
        case flagCorpHangar6: return (roles & Corp::Role::HangarCanTake6) != 0;
        case flagCorpHangar7: return (roles & Corp::Role::HangarCanTake7) != 0;
        default: return false;
    }
}

/** Locate a stack at station owned by contributor with enough qty. Corp acceptance uses the pilot's active wallet division hangar only and requires HangarCanTakeN. */
int FindRequestStackInStationHangars(Inventory* inv, uint16 typeID, uint32 qty, uint32 contributorOwnerID, bool acceptorForCorp, Client* client)
{
    if (acceptorForCorp) {
        if (client == nullptr)
            return 0;
        EVEItemFlags fl = flagHangar;
        if (!CorpWalletKeyToHangarFlag(client->GetCorpAccountKey(), fl))
            return 0;
        if (!CorpHangarTakeAllowed(client, fl))
            return 0;
        std::vector<InventoryItemRef> itemVec;
        inv->GetItemsByFlag(fl, itemVec);
        for (const auto& cur : itemVec)
            if (cur->ownerID() == contributorOwnerID && cur->typeID() == typeID && cur->quantity() >= qty)
                return cur->itemID();
        return 0;
    }
    std::vector<InventoryItemRef> itemVec;
    inv->GetItemsByFlag(flagHangar, itemVec);
    for (const auto& cur : itemVec)
        if (cur->ownerID() == contributorOwnerID && cur->typeID() == typeID && cur->quantity() >= qty)
            return cur->itemID();
    return 0;
}

/** Courier accepted-for-corp persists accepting corp + wallet division — ledger routing must use the corp row, and session corp must match. */
bool ValidateCorpCourierAcceptSession(Client* client, int acceptorWalletKeyRaw, uint32 acceptorCorpIDPersisted)
{
    if (acceptorWalletKeyRaw == 0)
        return true;
    if (acceptorCorpIDPersisted == 0u) {
        client->SendNotifyMsg(
            "This courier contract is missing persisted corporation acceptance metadata. Apply pending SQL migrations or recreate the contract.");
        return false;
    }
    if (!IsPlayerCorp(acceptorCorpIDPersisted)) {
        client->SendNotifyMsg("Invalid accepting corporation recorded on this contract.");
        return false;
    }
    if (client->GetCorporationID() != acceptorCorpIDPersisted) {
        client->SendNotifyMsg(
            "You must be in the same corporation that accepted this courier contract (for corporation collateral) to complete or fail it.");
        return false;
    }
    return true;
}

/** After `ctrContracts` insert: reverse create-time wallet effects, return traded items from escrow owner `1`, delete rows. */
void RollbackCreateContractAfterInsert(
    Client* client,
    uint32 contractId,
    int contractType,
    uint32 rewardAmount,
    bool forCorp,
    bool corpSccEscrowDone,
    const std::vector<int>& itemsMovedToContractEscrow,
    uint32 expectedOwnerID,
    uint16 issuerMoneyKeyForCorpRollback)
{
    if (contractId == 0u)
        return;

    for (int movedId : itemsMovedToContractEscrow) {
        InventoryItemRef ref = sItemFactory.GetItemRef(movedId);
        if (ref.get() != nullptr)
            ref->ChangeOwner(expectedOwnerID, true);
    }

    if (client != nullptr) {
        if (corpSccEscrowDone && contractType == 3 && rewardAmount > 0u && forCorp) {
            try {
                AccountService::TransferFunds(
                    corpSCC,
                    client->GetCorporationID(),
                    static_cast<double>(rewardAmount),
                    "Rollback courier contract reward escrow",
                    Journal::EntryType::ContractCollateralRefund,
                    contractId,
                    Account::KeyType::Cash,
                    issuerMoneyKeyForCorpRollback,
                    client);
            } catch (const std::exception& ex) {
                codelog(SERVICE__ERROR, "RollbackCreateContractAfterInsert: reverse corp SCC escrow failed for contract %u: %s", contractId, ex.what());
            } catch (...) {
                codelog(SERVICE__ERROR, "RollbackCreateContractAfterInsert: reverse corp SCC escrow failed for contract %u", contractId);
            }
        } else if (contractType == 3 && rewardAmount > 0u && !forCorp) {
            client->AddBalance(static_cast<double>(rewardAmount));
        }
    }

    DBerror err;
    if (!sDatabase.RunQuery(err, "DELETE FROM ctrItems WHERE contractId = %u", contractId))
        codelog(DATABASE__ERROR, "RollbackCreateContractAfterInsert: ctrItems delete for %u: %s", contractId, err.c_str());
    if (!sDatabase.RunQuery(err, "DELETE FROM ctrContracts WHERE contractId = %u", contractId))
        codelog(DATABASE__ERROR, "RollbackCreateContractAfterInsert: ctrContracts delete for %u: %s", contractId, err.c_str());
}

} // namespace

ContractProxy::ContractProxy () :
    Service("contractProxy")
{
    this->Add("GetContract", &ContractProxy::GetContract);
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs &,PyInt*, PyBool*, std::optional <PyNone*>, PyInt*, PyInt*, PyInt*, std::optional<PyNone*>, PyInt*, PyInt*, PyInt*, PyString*, PyString*)> (&ContractProxy::CreateContract));
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs &,PyInt*, PyBool*, std::optional <PyInt*>, PyInt*, PyInt*, PyInt*, std::optional<PyNone*>, PyInt*, PyInt*, PyInt*, PyString*, PyString*)> (&ContractProxy::CreateContract));
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs &,PyInt*, PyBool*, std::optional <PyInt*>, PyInt*, PyInt*, PyInt*, std::optional<PyNone*>, PyInt*, PyInt*, PyInt*, PyWString*, PyString*)> (&ContractProxy::CreateContract));
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs &,PyInt*, PyBool*, std::optional <PyNone*>, PyInt*, PyInt*, PyInt*, std::optional<PyInt*>, PyInt*, PyInt*, PyInt*, PyString*, PyString*)> (&ContractProxy::CreateContract));
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs &,PyInt*, PyBool*, std::optional <PyNone*>, PyInt*, PyInt*, PyInt*, std::optional <PyNone*>, PyInt*, PyInt*, PyInt*, PyWString*,PyString*)> (&ContractProxy::CreateContract));
    this->Add("CreateContract", static_cast <PyResult(ContractProxy::*)(PyCallArgs&, PyInt*, PyInt*, std::optional <PyInt*>, PyInt*, PyInt*, PyInt*, std::optional<PyInt*>, PyInt*, PyInt*, PyInt*, PyWString*, PyWString*)> (&ContractProxy::CreateContract));
    this->Add("DeleteContract", &ContractProxy::DeleteContract);
    this->Add("AcceptContract", static_cast<PyResult (ContractProxy::*)(PyCallArgs &, PyInt*)>(&ContractProxy::AcceptContract));
    this->Add("AcceptContract", static_cast<PyResult (ContractProxy::*)(PyCallArgs &, PyInt*, std::optional<PyBool*>)>(&ContractProxy::AcceptContract));
    this->Add("CompleteContract", &ContractProxy::CompleteContract);
    this->Add("GetLoginInfo", &ContractProxy::GetLoginInfo);
    this->Add("SearchContracts", &ContractProxy::SearchContracts);
    this->Add("NumOutstandingContracts", &ContractProxy::NumOutstandingContracts);
    this->Add("CollectMyPageInfo", &ContractProxy::CollectMyPageInfo);
    this->Add("GetItemsInStation", &ContractProxy::GetItemsInStation);
    this->Add("GetContractListForOwner", &ContractProxy::GetContractListForOwner);
    this->Add("GetMyExpiredContractList", &ContractProxy::GetMyExpiredContractList);
    /*
     *
            ret = self.contractSvc.CompleteContract(contractID, const.conStatusFinished)
            return self.contractSvc.CompleteContract(contractID, const.conStatusRejected)
            return self.contractSvc.PlaceBid(contractID, bid, forCorp)
            return self.contractSvc.FinishAuction(contractID, isIssuer)
            ret = self.contractSvc.SplitStack(stationID, itemID, qty, forCorp, flag)
            return self.contractSvc.GetItemsInContainer(stationID, containerID, forCorp, flag)
            return self.contractSvc.GetItemsInStation(stationID, forCorp)
            return self.contractSvc.DeleteNotification(contractID, forCorp)
            info = self.contractSvc.GetCourierContractFromItemID(itemID)
     */
}

PyResult ContractProxy::SearchContracts(PyCallArgs &call) {
    auto namedRep = [&call](const char* key) -> PyRep* {
        auto it = call.byname.find(key);
        return it != call.byname.end() ? it->second : nullptr;
    };
    auto namedPresentNotNone = [&namedRep](const char* key) -> bool {
        PyRep* r = namedRep(key);
        return r != nullptr && !r->IsNone();
    };

    // We will not proceed, if contractType is not specified (missing key or None).
    if (!namedPresentNotNone("contractType")) {
        codelog(SERVICE__ERROR, "%s: ContractType was not specified. Aborting search", GetName());
        return nullptr;
    }

    PyRep* contractTypeRep = namedRep("contractType");
    int contractType = 0;
    if (contractTypeRep != nullptr && contractTypeRep->IsInt()) {
        contractType = contractTypeRep->AsInt()->value();
    } else if (contractTypeRep != nullptr && contractTypeRep->IsLong()) {
        contractType = static_cast<int>(contractTypeRep->AsLong()->value());
    } else {
        codelog(SERVICE__ERROR, "%s: ContractType must be int or long. Aborting search", GetName());
        return nullptr;
    }

        /**
         * We're using sort of query constructor here - if request have certain value specified, we add it as another AND block.
         * For now, we will only filter by contract type, item type, item category, min/max price, min/max reward, location/end location, issuer and availability
         */
        std::string query = "SELECT cC.contractId FROM ctrContracts cC "
                            "JOIN ctrItems cI on cC.contractId = cI.contractId "
                            "JOIN entity e on cI.itemID = e.itemID "
                            "JOIN invTypes iT on iT.typeID = e.typeID "
                            "JOIN invGroups iG on iG.groupID = iT.groupID "
                            "JOIN invCategories iC on iG.categoryID = iC.categoryID "
                            "WHERE cC.contractType IN " + std::string(contractType == 10 ? "(1,2)" : "(" + std::to_string(contractType) + ")");
                                                         // Type 10 is "All" and "Exclude WTB", for some reason. We'll assume it's "All", lol

        if (namedPresentNotNone("itemTypes")) {
            PyList* itemTypes = namedRep("itemTypes")->AsObjectEx()->header()->AsTuple()->GetItem(1)->AsTuple()->GetItem(0)->AsList();
            std::string types;
            for (auto index = 0; index < itemTypes->size(); index++) {
                types.append(std::to_string(itemTypes->GetItem(index)->AsInt()->value()));
                if (index != itemTypes->size() - 1) {
                    types.append(",");
                }
            }

            if (!types.empty()) {
                query.append(" AND e.typeID IN (" + types + ")");
            }
        }

        if (namedPresentNotNone("itemGroupID")) {
            query.append(" AND iG.groupID = " + std::to_string(namedRep("itemGroupID")->AsInt()->value()));
        }
        if (namedPresentNotNone("itemCategoryID")) {
            query.append(" AND iC.categoryID = " + std::to_string(namedRep("itemCategoryID")->AsInt()->value()));
        }
        if (namedPresentNotNone("minPrice")) {
            query.append(" AND cC.price >= " + std::to_string(namedRep("minPrice")->AsInt()->value()));
        }
        if (namedPresentNotNone("maxPrice")) {
            query.append(" AND cC.price <= " + std::to_string(namedRep("maxPrice")->AsInt()->value()));
        }
        if (namedPresentNotNone("minReward")) {
            query.append(" AND cC.reward >= " + std::to_string(namedRep("minReward")->AsInt()->value()));
        }
        if (namedPresentNotNone("maxReward")) {
            query.append(" AND cC.reward <= " + std::to_string(namedRep("maxReward")->AsInt()->value()));
        }
        if (namedPresentNotNone("availability")) {
            int availability = namedRep("availability")->AsInt()->value();
            if (availability == 0) {
                // Public contracts
                query.append(" AND cC.isPrivate = 0");
            } else if (availability == 1) {
                // Private contracts, assigned to character
                query.append(" AND cC.isPrivate = 1 AND cC.assigneeId = " + std::to_string(call.client->GetCharacterID()));
            } else if(availability == 2) {
                // Private contracts, assigned to corp
                query.append(" AND cC.isPrivate = 1 AND cC.assigneeId = " + std::to_string(call.client->GetCorporationID()));
            }
        }
        // According to what i had during testing, locationID can only be system, constellation or region. Given that we only store system and region ID, we use OR clause for these
        if (namedPresentNotNone("locationID")) {
            int locationId = namedRep("locationID")->AsInt()->value();
            if (IsSolarSystemID(locationId)) {
                // Solar system range
                query.append(" AND cC.startSolarSystemID = " + std::to_string(locationId));
            } else if (IsRegionID(locationId)) {
                // Region range
                query.append(" AND cC.startRegionID = " + std::to_string(locationId));
            }
        }
        // Same applies to endLocationID - it uses the same search::QuickQuery() call to get it
        if (namedPresentNotNone("endLocationID")) {
            int locationId = namedRep("endLocationID")->AsInt()->value();
            if (IsSolarSystemID(locationId)) {
                // Solar system range
                query.append(" AND cC.endSolarSystemID = " + std::to_string(locationId));
            } else if (IsRegionID(locationId)) {
                // Region range
                query.append(" AND cC.endRegionID = " + std::to_string(locationId));
            }
        }
        // Once again, issuer can be either a character or a corporation. We use separate filters depending on value
        if (namedPresentNotNone("issuerID")) {
            int issuerId = namedRep("issuerID")->AsInt()->value();
            if (IsCorp(issuerId)) {
                // Corporation case
                query.append(" AND cC.issuerCorpID = " + std::to_string(issuerId) + " AND cC.forCorp = true");
            } else {
                query.append(" AND cC.issuerID = " + std::to_string(issuerId) + " AND cC.forCorp = false");
            }
        }
        query.append(" AND cC.status = 0");
        /**
         * Once query is constructed, we execute it and collect contractID's. Since we can have duplicate values, we first
         * collect it to std::vector, and then we pass it to GetContractEntries function
         */

        DBQueryResult contractRes;
        if (!sDatabase.RunQuery(contractRes, query.c_str()))
        {
            codelog(DATABASE__ERROR, "Error in query: %s", contractRes.error.c_str());
            return nullptr;
        }
        std::vector<int> contractIDs;
        DBResultRow contractRow;
        while (contractRes.GetRow(contractRow)) {
            int contractId = contractRow.GetInt(0);

            // To make sure we don't add duplicates, we check whether we already have said contractID in vector already.
            if (std::find(contractIDs.begin(), contractIDs.end(), contractId) == contractIDs.end()) {
                contractIDs.push_back(contractId);
            }
        }

        PyDict* response = new PyDict;
        PyList* contracts = ContractUtils::GetContractEntries(contractIDs);
        response->SetItemString("contracts", contracts ? contracts : new PyList);
        response->SetItemString("numFound", contracts ? new PyInt(contracts->size()) : new PyInt(0));
        response->SetItemString("searchTime", new PyInt(153));  // Since search time is of no relevance to the client, we simply hard-code it
        response->SetItemString("maxResults", new PyInt(1000)); // Same here - we do not limit the list of contracts queried, so we leave this value hard-coded

    return new PyObject("util.KeyVal", response);
}

PyResult ContractProxy::CreateContract(PyCallArgs &call,
    PyInt* contractType, PyBool* isPrivate, std::optional <PyNone*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyNone*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyString* title, PyString* description) {
    return CreateContract(call, contractType, new PyInt(isPrivate->value()), std::nullopt, expireTime, duration, startStationID, std::nullopt, price, reward, collateral, new PyWString(title->content()), new PyWString(description->content()));
}

PyResult ContractProxy::CreateContract(PyCallArgs &call,
    PyInt* contractType, PyBool* isPrivate, std::optional <PyInt*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyNone*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyString* title, PyString* description) {
    return CreateContract(call, contractType, new PyInt(isPrivate->value()), assigneeID, expireTime, duration, startStationID, std::nullopt, price, reward, collateral, new PyWString(title->content()), new PyWString(description->content()));
}

PyResult ContractProxy::CreateContract(PyCallArgs &call,
    PyInt* contractType, PyBool* isPrivate, std::optional <PyInt*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyNone*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyWString* title, PyString* description) {
    return CreateContract(call, contractType, new PyInt(isPrivate->value()), assigneeID, expireTime, duration, startStationID, std::nullopt, price, reward, collateral, title, new PyWString(description->content()));
}

PyResult ContractProxy::CreateContract(PyCallArgs &call,
    PyInt* contractType, PyBool* isPrivate, std::optional <PyNone*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyInt*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyString* title, PyString* description) {
    return CreateContract(call, contractType, new PyInt(isPrivate->value()), std::nullopt, expireTime, duration, startStationID, endStationID, price, reward, collateral, new PyWString(title->content()), new PyWString(description->content()));
}

PyResult ContractProxy::CreateContract(PyCallArgs &call,
    PyInt* contractType, PyBool* isPrivate, std::optional <PyNone*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyNone*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyWString* title, PyString* description) {
    return CreateContract(call, contractType, new PyInt(isPrivate->value()), std::nullopt, expireTime, duration, startStationID, std::nullopt, price, reward, collateral, title, new PyWString(description->content()));
}


PyResult ContractProxy::CreateContract(PyCallArgs &call, 
    PyInt* contractType, PyInt* isPrivate, std::optional <PyInt*> assigneeID, PyInt* expireTime, PyInt* duration, PyInt* startStationID, std::optional<PyInt*> endStationID,
    PyInt* price, PyInt* reward, PyInt* collateral, PyWString* title, PyWString* description) {
    int startStationDivision, startSystemId, startRegionId, endSystemId, endRegionId;
    bool forCorp;

    /**
     * Since named args (byname) aren't included in packet, we process them separately.
     */
    if (call.byname.find("flag")->second->IsInt()) {
        startStationDivision = call.byname.find("flag")->second->AsInt()->value();
    } else {
        codelog(SERVICE__ERROR, "startStationDivision value is of invalid type");
        return nullptr;
    }
    if (call.byname.find("forCorp")->second->IsBool()) {
        forCorp = call.byname.find("forCorp")->second->AsBool()->value();
    } else {
        codelog(SERVICE__ERROR, "forCorp value is of invalid type");
        return nullptr;
    }
    if (sDataMgr.IsStation(startStationID->value())) {
        startSystemId = sDataMgr.GetStationSystem(startStationID->value());
        startRegionId = sDataMgr.GetStationRegion(startStationID->value());
    } else {
        codelog(SERVICE__ERROR, "Specified start Station ID has no Station counterparts in DB");
        return nullptr;
    }
    if (endStationID.has_value()) {
        if (sDataMgr.IsStation(endStationID.value()->value())) {
            endSystemId = sDataMgr.GetStationSystem(endStationID.value()->value());
            endRegionId = sDataMgr.GetStationRegion(endStationID.value()->value());
        } else {
            codelog(SERVICE__ERROR, "Specified end Station ID has no Station counterparts in DB");
            return nullptr;
        }
    } else {
        endSystemId = startSystemId;
        endRegionId = 0;
    }

    const uint32 issuerWalletKeyInsert = forCorp ? static_cast<uint32>(call.client->GetCorpAccountKey()) : 0u;

    // Courier reward: personal issuer pre-debits character wallet before the row exists (historic behavior).
    // Corporation issuer: validate the listing division balance here; escrow corp → SCC after insert (pairs with CompleteContract paying from SCC).
    if (contractType->value() == 3 && reward->value() > 0) {
        if (forCorp) {
            if (!IsPlayerCorp(call.client->GetCorporationID())) {
                call.client->SendNotifyMsg("You must belong to a player corporation to create a courier contract for your corporation.");
                return nullptr;
            }
            const uint16 divKey = static_cast<uint16>(issuerWalletKeyInsert);
            if (AccountDB::GetCorpBalance(call.client->GetCorporationID(), divKey) < reward->value()) {
                call.client->SendNotifyMsg("Your corporation does not have enough ISK to pay the reward");
                return nullptr;
            }
        } else {
            if (call.client->GetBalance() < reward->value()) {
                call.client->SendNotifyMsg("You do not have enough ISK to pay the reward");
                return nullptr;
            }
            call.client->AddBalance(-static_cast<double>(reward->value()));
        }
    }

    /**
     * Then, we go for actual entries creation.
     * Contract entry
     */
    uint32 contractId = 0;
    DBerror err;
    if (!sDatabase.RunQueryLID(err, contractId,
        "INSERT INTO ctrContracts "
        "(contractType, issuerID, issuerCorpID, forCorp, isPrivate, assigneeID, "
        "dateIssued, dateExpired, expireTimeInMinutes, duration, numDays, "
        "startStationID, startSolarSystemID, startRegionID, endStationID, endSolarSystemID, endRegionID, "
        "price, reward, collateral, title, description, issuerAllianceID, startStationDivision, issuerWalletKey) "
        "VALUES "
        "(%u, %u, %u, %u, %u, %u, "
        "%lli, %lli, %u, %u, %u, "
        "%u, %u, %u, %u, %u, %u,"
        "%u, %u, %u, '%s', '%s', %u, %u, %u)",
        contractType->value(), call.client->GetCharacterID(), call.client->GetCorporationID(), forCorp, isPrivate->value()?1:0, assigneeID.has_value() ? assigneeID.value()->value() : 0,
        int64(GetFileTimeNow()), int64(GetRelativeFileTime(0, 0, expireTime->value())), expireTime->value(), duration->value(), expireTime->value() / 1440,
        startStationID->value(), startSystemId, startRegionId, endStationID.has_value() ? endStationID.value()->value() : 0, endSystemId, endRegionId,
        price->value(), reward->value(), collateral->value(), title->content().c_str(), description->content().c_str(), call.client->GetAllianceID(), startStationDivision, issuerWalletKeyInsert))
    {
        codelog(DATABASE__ERROR, "Failed to insert new entity: %s", err.c_str());
        return nullptr;
    }

    bool corpSccEscrowDone = false;
    if (contractType->value() == 3 && reward->value() > 0 && forCorp) {
        const uint16 divKey = static_cast<uint16>(issuerWalletKeyInsert);
        AccountService::TransferFunds(
            call.client->GetCorporationID(),
            corpSCC,
            static_cast<double>(reward->value()),
            "Courier contract reward escrow",
            Journal::EntryType::ContractCollateral,
            contractId,
            divKey,
            Account::KeyType::Cash,
            call.client
        );
        corpSccEscrowDone = true;
    }

    /**
     * Then, we insert the items.
     * First off, we gather the list of attributes for these items, using select query.
     * To save resources and reduce amount of DB hits, we compose the query by adding ID's first, then we execute it separately.
     */
    std::string itemsToInsert;
    float totalVolume = 0.00;
    std::vector<int> itemsMovedToContractEscrow;
    const uint32 expectedTradedOwnerRollback = forCorp ? call.client->GetCorporationID() : call.client->GetCharacterID();
    const uint16 issuerMoneyKeyRollback = issuerWalletKeyInsert != 0u
        ? static_cast<uint16>(issuerWalletKeyInsert)
        : static_cast<uint16>(Account::KeyType::Cash);
    if (call.byname.find("itemList")->second->IsList()) {
        PyList *tradedItems = call.byname.find("itemList")->second->AsList();
        if (!tradedItems->empty()) {
            //TODO: We need to account for items that can be packed in a container/ship/container inside the ship
            std::string query = "SELECT entity.itemID, entity.ownerID, entity.typeID, entity.quantity, entity.locationID, iB.pLevel, "
                                "       iB.mLevel, iB.copy, iB.runs, ea.valueInt as damage, entity.flag "
                                "FROM entity "
                                "LEFT JOIN invBlueprints iB on entity.itemID = iB.itemID "
                                "LEFT JOIN entity_attributes ea on entity.itemID = ea.itemID and ea.attributeID = 3 "
                                "WHERE entity.itemID IN (%s)";
            std::string queryIds;
            std::map<int, int> expectedQuantities;              // Key is itemID, value is quantity. We use map to save time on list iteration
            for (int index = 0; index < tradedItems->size(); index++) {
                PyList *tradedItem = tradedItems->GetItem(index)->AsList();
                int itemID = tradedItem->GetItem(0)->AsInt()->value();
                int quantity = tradedItem->GetItem(1)->AsInt()->value();

                queryIds.append(std::to_string(itemID));
                expectedQuantities[itemID] = quantity;

                // if it's not the last item - add a trailing comma
                if (index != tradedItems->size() - 1) {
                    queryIds.append(", ");
                }
            }

            DBQueryResult res;
            if (!sDatabase.RunQuery(res,query.c_str(), queryIds.c_str()))
            {
                codelog(DATABASE__ERROR, "Error in query: %s", res.error.c_str());
                RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                    static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                    itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
                return nullptr;
            }

            /**
             * I HATE the fact that i have to do the same bloody loop again, but we didn't have DB values prior to that.
             * We need to validate traded items exist, have correct owner and quantities. Any item that fails the check is excluded from the list.
             */
             DBResultRow row;
             Inventory* stationInvForCourierVol = nullptr;
             if (contractType->value() == 3) {
                 StationItemRef stRef = sItemFactory.GetStationRef(startStationID->value());
                 if (stRef.get() != nullptr)
                     stationInvForCourierVol = stRef->GetMyInventory();
             }
             // We work directly with DBQueryResult since resulting CRowSet does not fit ctrItems format - thus, it would be needless processing.
             while(res.GetRow(row)) {
                 int itemID = row.GetInt(0);
                 int ownerID = row.GetInt(1);
                 int quantity = row.GetInt(3);
                 int parentID = row.GetInt(4) >= 14000000 ? row.GetInt(4) : 0;
                 int pLevel = row.IsNull(5) ? 0 : row.GetInt(5);
                 int mLevel = row.IsNull(6) ? 0 : row.GetInt(6);
                 int isCopy = row.IsNull(7) ? 0 : (row.GetBool(7) ? 1 : 0);
                 int runs = row.IsNull(8) ? 0 : row.GetInt(8);
                 int damage = row.IsNull(9) ? 0 : row.GetInt(9);
                 int flag = row.IsNull(10) ? 0 : row.GetInt(10);

                 const auto exIt = expectedQuantities.find(itemID);
                 if (exIt == expectedQuantities.end())
                     continue;
                 if (static_cast<uint32>(ownerID) == expectedTradedOwnerRollback && quantity == exIt->second) {
                     InventoryItemRef tradedRef = sItemFactory.GetItemRef(itemID);
                     if (tradedRef.get() == nullptr) {
                         codelog(SERVICE__ERROR, "%s: CreateContract traded item %d not loaded after DB validation.", GetName(), itemID);
                         RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                             static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                             itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
                         return nullptr;
                     }

                     if (contractType->value() == 3) {
                         if (stationInvForCourierVol == nullptr) {
                             codelog(SERVICE__ERROR, "%s: CreateContract courier contract needs station inventory for volume.", GetName());
                             RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                                 static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                                 itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
                             return nullptr;
                         }
                         InventoryItemRef volStack = stationInvForCourierVol->GetByID(itemID);
                         if (volStack.get() == nullptr) {
                             codelog(SERVICE__ERROR, "%s: CreateContract courier volume: item %d not in station inventory.", GetName(), itemID);
                             RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                                 static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                                 itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
                             return nullptr;
                         }
                         totalVolume += volStack->GetAttribute(161).get_float() * static_cast<float>(quantity);
                     }

                     itemsToInsert.append("(" + std::to_string(contractId) + ", " +
                        std::to_string(itemID) + ", " +
                        std::to_string(quantity) + ", " +
                        row.GetText(2) + ", " +
                        "1, " +
                        std::to_string(parentID) + ", " +
                        std::to_string(pLevel) + ", " +
                        std::to_string(mLevel) + ", " +
                        std::to_string(isCopy) + "," +
                        std::to_string(runs) + ", " +
                        std::to_string(damage) + ", " +
                        std::to_string(flag)+ "),");

                     tradedRef->ChangeOwner(1, true);
                     itemsMovedToContractEscrow.push_back(itemID);
                 }
             }
        }
    }


    if (call.byname.find("requestItemTypeList")->second->IsList()) {
        PyList *requestedItems = call.byname.find("requestItemTypeList")->second->AsList();
        if (!requestedItems->empty()) {
            for (int index = 0; index < requestedItems->size(); index++) {
                PyList *requestedItem = requestedItems->GetItem(index)->AsList();
                itemsToInsert.append("(" + std::to_string(contractId) + ", " +
                                     "0, " +
                                     std::to_string(requestedItem->GetItem(1)->AsInt()->value()) + ", " +
                                     std::to_string(requestedItem->GetItem(0)->AsInt()->value()) + ", " +
                                     "0, 0, 0, 0, 0, 0, 0, 0),");
            }
        }
    }

    if(!itemsToInsert.empty()) {
        itemsToInsert.pop_back();
        std::string query = "INSERT INTO ctrItems (contractId, itemID, quantity, itemTypeID, inCrate, parentID, "
                            "productivityLevel, materialLevel, isCopy, licensedProductionRunsRemaining, damage, flagID) "
                            "VALUES " + itemsToInsert;
        uint32 last_insert;
        if (!sDatabase.RunQueryLID(err, last_insert, query.c_str()))
        {
            codelog(DATABASE__ERROR, "Failed to insert new entity: %s", err.c_str());
            RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
            return nullptr;
        }

        // We only insert volume for courier-type contracts - the other types don't use this value.
        if (contractType->value() == 3) {
            DBerror volErr;
            if (!sDatabase.RunQuery(volErr,
                                    "UPDATE ctrContracts SET volume = %f WHERE contractId = %u", totalVolume, contractId))
            {
                codelog(DATABASE__ERROR, "Failed to update contract volume: %s", volErr.c_str());
                RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
                    static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
                    itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
                return nullptr;
            }
        }

    } else {
        codelog(SERVICE__ERROR, "No traded or requested items was specified. Aborting");
        RollbackCreateContractAfterInsert(call.client, contractId, contractType->value(),
            static_cast<uint32>(reward->value()), forCorp, corpSccEscrowDone,
            itemsMovedToContractEscrow, expectedTradedOwnerRollback, issuerMoneyKeyRollback);
        return nullptr;
    }

    return new PyInt((int) contractId);
}

PyResult ContractProxy::DeleteContract(PyCallArgs &call, PyInt* contractID) {
    sLog.White( "ContractProxy::Handle_DeleteContract()", "size=%lu", call.tuple->size());
    call.Dump(SERVICE__CALL_DUMP);

    bool issuerForCorp = false;
    int contractType = 0;
    int contractReward = 0;
    int contractStatus = 0;
    int issuerWalletKeyRaw = 0;
    uint32 issuerCorpIDRow = 0;
    {
        DBQueryResult resIss;
        if (!sDatabase.RunQuery(resIss,
                               "SELECT forCorp, issuerID, contractType, reward, status, issuerWalletKey, issuerCorpID "
                               "FROM ctrContracts WHERE contractId = %u",
                               contractID->value())
            || resIss.GetRowCount() == 0) {
            return new PyBool(false);
        }
        DBResultRow rfc;
        resIss.GetRow(rfc);
        issuerForCorp = rfc.GetBool(0);
        if (static_cast<uint32>(rfc.GetInt(1)) != call.client->GetCharacterID()) {
            return new PyBool(false);
        }
        contractType = rfc.GetInt(2);
        contractReward = rfc.GetInt(3);
        contractStatus = rfc.GetInt(4);
        issuerWalletKeyRaw = rfc.GetInt(5);
        issuerCorpIDRow = rfc.GetUInt(6);
    }
    const uint32 itemOwnerRestore = issuerForCorp ? issuerCorpIDRow : call.client->GetCharacterID();

    // Outstanding courier: return reward — personal was debited at create; corp issuer funds were moved to SCC at create.
    if (contractType == 3 && contractReward > 0 && contractStatus == 0) {
        if (issuerForCorp) {
            const uint16 issuerMoneyKey = issuerWalletKeyRaw != 0 ? static_cast<uint16>(issuerWalletKeyRaw) : Account::KeyType::Cash;
            AccountService::TransferFunds(
                corpSCC,
                issuerCorpIDRow,
                static_cast<double>(contractReward),
                "Courier contract reward refund on delete",
                Journal::EntryType::ContractCollateralRefund,
                contractID->value(),
                Account::KeyType::Cash,
                issuerMoneyKey,
                call.client
            );
        } else {
            call.client->AddBalance(static_cast<double>(contractReward));
        }
    }

    // In order to return items back to the owner, we need a full list of entityID's to return. We gather them using utils function
    std::vector<int> entityIds;
    ContractUtils::GetContractItemIDs(contractID->value(), &entityIds);
    for (auto entityID : entityIds) {
        // We have to put in couple layers of checks here. First one will cut requested item entries out of the equation
        if (entityID != 0) {
            // We have to check if we actually got the item ref - in case of invalid entity ID specified.
            InventoryItemRef ref = sItemFactory.GetItemRef(entityID);
            if (ref) {
                ref->ChangeOwner(itemOwnerRestore, true);
            } else {
                continue;
            }
        }
    }

    DBerror err;
    if (!sDatabase.RunQuery(err,
                            "UPDATE ctrContracts SET status = 8 WHERE contractId = %u", contractID->value()))
    {
        codelog(DATABASE__ERROR, "Failed to update contract volume: %s", err.c_str());
    }

    return new PyBool(true);
}

PyResult ContractProxy::GetContract(PyCallArgs &call, PyInt* contractID) {
    return ContractUtils::GetContractEntry(contractID->value());
}

PyResult ContractProxy::AcceptContract(PyCallArgs &call, PyInt* contractID) {
    return AcceptContract(call, contractID, std::nullopt);
}

PyResult ContractProxy::AcceptContract(PyCallArgs &call, PyInt* contractID, std::optional<PyBool*> acceptorForCorpArg) {
    PyBool* const acceptorForCorpBool = acceptorForCorpArg.has_value() ? acceptorForCorpArg.value() : nullptr;
    const bool acceptorForCorp = acceptorForCorpBool != nullptr && acceptorForCorpBool->value();

    DBQueryResult res;
    if (!sDatabase.RunQuery(res,
                            "SELECT contractType, status, price, reward, collateral, volume, startStationID, issuerID, issuerCorpID, forCorp, startSolarSystemID, endSolarSystemID, issuerWalletKey "
                            "FROM ctrContracts WHERE contractId = %u",
                            contractID->value()))
    {
        codelog(DATABASE__ERROR, "Error in query: %s", res.error.c_str());
        return nullptr;
    }
    if (res.GetRowCount() == 0) {
        return nullptr;
    }
    DBResultRow row;
    res.GetRow(row);
    int contractType = row.GetInt(0);
    int status = row.GetInt(1);
    int price = row.GetInt(2);
    int reward = row.GetInt(3);
    int collateral = row.GetInt(4);
    float volume = row.GetFloat(5);
    int startStationID = row.GetInt(6);
    int issuerID = row.GetInt(7);
    uint32 issuerCorpID = row.GetUInt(8);
    bool issuerForCorp = row.GetBool(9);
    int startSolarSystemID = row.GetInt(10);
    int endSolarSystemID = row.GetInt(11);
    const int issuerWalletKeyRaw = row.GetInt(12);

    const uint32 issuerWalletID = issuerForCorp ? issuerCorpID : static_cast<uint32>(issuerID);
    const uint32 acceptorItemOwnerID = acceptorForCorp ? call.client->GetCorporationID() : call.client->GetCharacterID();
    const uint16 issuerMoneyKey = issuerWalletKeyRaw != 0 ? static_cast<uint16>(issuerWalletKeyRaw) : Account::KeyType::Cash;
    const uint16 acceptorMoneyKey = acceptorForCorp ? static_cast<uint16>(call.client->GetCorpAccountKey()) : Account::KeyType::Cash;

    if (status == 0) {
        // We can only accept outstanding contracts. If it's not - we ignore the call.
        int64 timestamp = int64(GetFileTimeNow());
        switch (contractType) {
            case 1: {
                // Item Exchange
                // We start off by gathering traded and requested items
                std::vector<int> tradedItems;
                std::map<int, int> requestedItems;
                ContractUtils::GetContractItemIDs(contractID->value(), &tradedItems);
                ContractUtils::GetRequestedItems(contractID->value(), &requestedItems);

                Inventory* stationInv = sItemFactory.GetStationRef(startStationID)->GetMyInventory();

                // Next, we perform checks to make sure we fit all contract requirements. I won't do it by nesting if loops - i'll just use trigger booleans;
                bool iskRequirementMet(true), rewardRequirementMet(true), requestedItemsRequirementsMet(true);
                if (price > 0) {
                    if (acceptorForCorp) {
                        if (AccountDB::GetCorpBalance(call.client->GetCorporationID(), acceptorMoneyKey) < price)
                            iskRequirementMet = false;
                    } else if (call.client->GetBalance() < price) {
                        iskRequirementMet = false;
                    }
                }
                if (reward > 0) {
                    if (issuerForCorp) {
                        if (AccountDB::GetCorpBalance(issuerCorpID, issuerMoneyKey) < reward)
                            rewardRequirementMet = false;
                    } else if (AccountDB::GetCharacterISKBalance(static_cast<uint32>(issuerID)) < static_cast<double>(reward)) {
                        rewardRequirementMet = false;
                    }
                }
                if (!requestedItems.empty()) {
                    for (const auto& entry : requestedItems) {
                        if (FindRequestStackInStationHangars(stationInv, entry.first, entry.second, acceptorItemOwnerID, acceptorForCorp, acceptorForCorp ? call.client : nullptr) == 0)
                            requestedItemsRequirementsMet = false;
                    }
                }

                // Then, we go for acceptance
                if (iskRequirementMet && rewardRequirementMet && requestedItemsRequirementsMet) {
                    // Inventory first, then ISK — avoids partial settlement if requested/traded item steps fail or return early
                    // Then, we go for requested items
                    if (!requestedItems.empty()) {
                        for (auto entry : requestedItems) {
                            int entityID = FindRequestStackInStationHangars(stationInv, entry.first, entry.second, acceptorItemOwnerID, acceptorForCorp, acceptorForCorp ? call.client : nullptr);
                            if (entityID == 0) {
                                codelog(SERVICE__ERROR, "%s: AcceptContract item-exchange requested stack missing (typeID=%u qty=%u).", GetName(), entry.first, entry.second);
                                call.client->SendNotifyMsg("Required items are no longer available at this station.");
                                return nullptr;
                            }
                            InventoryItemRef stackRef = stationInv->GetByID(entityID);
                            if (stackRef.get() == nullptr) {
                                codelog(SERVICE__ERROR, "%s: AcceptContract GetByID(%d) null for requested stack.", GetName(), entityID);
                                call.client->SendNotifyMsg("Required items are no longer available at this station.");
                                return nullptr;
                            }
                            if (stackRef->quantity() > entry.second) {
                                // If located stack contains more than we need, we split it and transfer the required amount.
                                stackRef->Split(entry.second)->ChangeOwner(issuerWalletID, true);
                            } else {
                                // If not - we simply transfer it to issuer.
                                InventoryItemRef entRef = sItemFactory.GetItemRef(entityID);
                                if (entRef.get() == nullptr) {
                                    codelog(SERVICE__ERROR, "%s: AcceptContract GetItemRef(%d) null before ChangeOwner to issuer.", GetName(), entityID);
                                    call.client->SendNotifyMsg("Required items are no longer available at this station.");
                                    return nullptr;
                                }
                                entRef->ChangeOwner(issuerWalletID, true);
                            }
                        }
                    }

                    // And finally, we go for traded items
                    if (!tradedItems.empty()) {
                        for (auto item : tradedItems) {
                            InventoryItemRef tRef = sItemFactory.GetItemRef(item);
                            if (tRef.get() == nullptr) {
                                codelog(SERVICE__ERROR, "%s: AcceptContract traded item %d not loaded.", GetName(), item);
                                call.client->SendNotifyMsg("Contract traded items could not be loaded.");
                                return nullptr;
                            }
                            tRef->ChangeOwner(acceptorItemOwnerID, true);
                        }
                    }

                    // If we have a reward value - then contract's WTB
                    if (reward > 0) {
                        AccountService::TransferFunds(issuerWalletID,
                                                      acceptorItemOwnerID,
                                                      reward,
                                                      "Payment for accepted contract",
                                                      Journal::EntryType::ContractReward,
                                                      contractID->value(),
                                                      issuerMoneyKey,
                                                      acceptorMoneyKey,
                                                      call.client);
                    }

                    // If we have price value - then contract's WTS
                    if (price > 0) {
                        AccountService::TransferFunds(acceptorItemOwnerID,
                                                      issuerWalletID,
                                                      price,
                                                      "Payment for accepted contract",
                                                      Journal::EntryType::ContractPrice,
                                                      contractID->value(),
                                                      acceptorMoneyKey,
                                                      issuerMoneyKey,
                                                      call.client);
                    }

                    // Once all manipulations are done, we update contract status. Response is sent outside the switch clause;
                    DBerror err;
                    if (!sDatabase.RunQuery(err,
                                            "UPDATE ctrContracts SET status = 4, dateAccepted = %lli, dateCompleted = %lli, acceptorID = %u WHERE contractId = %u",
                                            timestamp, timestamp, call.client->GetCharacterID(), contractID))
                    {
                        codelog(DATABASE__ERROR, "Failed to update contract : %s", err.c_str());
                    }
                } else {
                    if (!iskRequirementMet) {
                        call.client->SendNotifyMsg("You have insufficient funds");
                        return nullptr;
                    }
                    if (!rewardRequirementMet) {
                        call.client->SendNotifyMsg("Issuer have insufficient funds to pay for the contract");
                        return nullptr;
                    }
                    if (!requestedItemsRequirementsMet) {
                        call.client->SendNotifyMsg("You do not have required items to accept this contract");
                        return nullptr;
                    }
                }
                break;
            }
            case 3:
            {
                // Courier contract
                // Collateral: character wallets use AddBalance; corporate acceptance escrows via the corp ledger → SCC (persist acceptorWalletKey for completion symmetry).
                const uint32 persistedAcceptorWalletKey = acceptorForCorp ? static_cast<uint32>(acceptorMoneyKey) : 0u;
                const uint32 persistedAcceptorCorpID = acceptorForCorp ? call.client->GetCorporationID() : 0u;

                if (collateral > 0) {
                    if (acceptorForCorp) {
                        if (!IsPlayerCorp(call.client->GetCorporationID())) {
                            call.client->SendNotifyMsg("You must belong to a player corporation to accept a courier contract for your corporation.");
                            return nullptr;
                        }
                        if (AccountDB::GetCorpBalance(call.client->GetCorporationID(), acceptorMoneyKey) < collateral) {
                            call.client->SendNotifyMsg("Your corporation does not have enough ISK to pay collateral");
                            return nullptr;
                        }
                        AccountService::TransferFunds(
                            call.client->GetCorporationID(),
                            corpSCC,
                            static_cast<double>(collateral),
                            "Courier contract collateral escrow",
                            Journal::EntryType::ContractCollateral,
                            contractID->value(),
                            acceptorMoneyKey,
                            Account::KeyType::Cash,
                            call.client
                        );
                    } else {
                        if (call.client->GetBalance() < collateral) {
                            call.client->SendNotifyMsg("You do not have enough ISK to pay collateral");
                            return nullptr;
                        }
                        call.client->AddBalance(-collateral);
                    }
                }

                /**
                 * Courier contract acceptance includes following steps:
                 * - Create a plastic wrap container
                 * - Set capacity and volume attribute to the volume of the contracted items
                 * - Move all items inside this container
                 * -
                 * - Give that container to the character
                 * - Update contract entry - move it to In Progress and leave a time-stamp when it was accepted.
                 */
                // Create container and set capacity and volume attributes;
                std::string containerName = sItemFactory.GetSolarSystemRef(startSolarSystemID)->name();
                containerName = containerName + " -> " + sItemFactory.GetSolarSystemRef(endSolarSystemID)->name() + "(" + std::to_string(volume) + "m3)";

                ItemData itemData(itemPlasticWrap, call.client->GetCharacterID(), locTemp, flagNone);
                itemData.name = containerName;
                InventoryItemRef plasticWrap = sItemFactory.SpawnItem(itemData);
                if (plasticWrap.get() != nullptr) {
                    plasticWrap->SetAttribute(AttrVolume, volume);
                    plasticWrap->SetAttribute(AttrCapacity, volume);
                }
                plasticWrap->SaveItem();
                // Then, move all required items into it
                std::vector<int> items;
                ContractUtils::GetContractItemIDs(contractID->value(), &items);
                for (auto item : items) {
                    InventoryItemRef itm = sItemFactory.GetItemRef(item);
                    if (itm.get() != nullptr) {
                        itm->Move(plasticWrap->itemID(), flagNone, true);
                        itm->ChangeOwner(call.client->GetCharacterID());
                    }
                }
                // And we give the container to the player
                plasticWrap->Move(startStationID, flagHangar, true);

                // Finally, we update DB entry
                DBerror err;
                if (!sDatabase.RunQuery(err,
                                        "UPDATE ctrContracts SET status = 1, dateAccepted = %lli, acceptorID = %u, crateID = %u, acceptorWalletKey = %u, acceptorCorpID = %u WHERE contractId = %u",
                                        timestamp, call.client->GetCharacterID(), plasticWrap->itemID(), persistedAcceptorWalletKey, persistedAcceptorCorpID, contractID))
                {
                    codelog(DATABASE__ERROR, "Failed to update contract : %s", err.c_str());
                }
                break;
            }
            default:
                // We do not expect anything abnormal.
                return nullptr;
        }
        // Once type-specific manipulations are done, we query brief contract information (requested by client) and send it out.
        if (!sDatabase.RunQuery(res, "SELECT contractId, contractType, startStationID, endStationID, dateAccepted, numDays FROM ctrContracts WHERE contractId = %u", contractID))
        {
            codelog(DATABASE__ERROR, "Error in query: %s", res.error.c_str());
            return nullptr;
        }

        // DBResultToCRowset return doesn't work, for some reason (fails at unmarshalling on client's side), so making it a KeyVal dict
        res.GetRow(row);
        PyDict* ret = new PyDict;
        ret->SetItemString("contractID", new PyInt(row.GetInt(0)));
        ret->SetItemString("type", new PyInt(row.GetInt(1)));
        ret->SetItemString("startStationID", new PyInt(row.GetInt(2)));
        ret->SetItemString("endStationID", new PyInt(row.GetInt(3)));
        ret->SetItemString("dateAccepted", new PyLong(row.GetInt64(4)));
        ret->SetItemString("numDays", new PyInt(row.GetInt(5)));
        return new PyObject("util.KeyVal", ret);
    } else {
        return nullptr;
    }
}


PyResult ContractProxy::CompleteContract(PyCallArgs &call, PyInt* contractID, PyInt* completionStatus) {
    call.Dump(SERVICE__CALL_DUMP);

    DBQueryResult res;
    // ctrContracts row layout (positional Get* below must stay in sync):
    // 0 contractType, 1 status, 2 price, 3 reward, 4 collateral, 5 volume, 6 startStationID, 7 endStationID,
    // 8 issuerID, 9 issuerCorpID, 10 forCorp, 11 acceptorID, 12 crateID, 13 acceptorWalletKey, 14 acceptorCorpID, 15 issuerWalletKey
    if (!sDatabase.RunQuery(res,
                            "SELECT contractType, status, price, reward, collateral, volume, startStationID, endStationID, issuerID, issuerCorpID, forCorp, acceptorID, crateID, acceptorWalletKey, acceptorCorpID, issuerWalletKey "
                            "FROM ctrContracts WHERE contractId = %u",
                            contractID))
    {
        codelog(DATABASE__ERROR, "Error in query: %s", res.error.c_str());
        return new PyBool(false);
    }
    if (res.GetRowCount() == 0) {
        return new PyBool(false);
    }
    DBResultRow row;
    res.GetRow(row);
    const int contractType = row.GetInt(0);
    const int status = row.GetInt(1);
    const int reward = row.GetInt(3);
    const int collateral = row.GetInt(4);
    const int startStationID = row.GetInt(6);
    const int endStationID = row.GetInt(7);
    const int issuerID = row.GetInt(8);
    const uint32 issuerCorpID = row.GetUInt(9);
    const bool issuerForCorp = row.GetBool(10);
    const uint32 acceptorCharID = row.GetUInt(11);
    const int crateID = row.GetInt(12);
    const int acceptorWalletKeyRaw = row.GetInt(13);
    const uint32 acceptorCorpIDPersisted = row.GetUInt(14);
    const int issuerWalletKeyRaw = row.GetInt(15);

    const uint32 issuerWalletID = issuerForCorp ? issuerCorpID : static_cast<uint32>(issuerID);
    const uint16 issuerMoneyKey = issuerWalletKeyRaw != 0 ? static_cast<uint16>(issuerWalletKeyRaw) : Account::KeyType::Cash;

    (void)status;
    (void)startStationID;

    int64 timestamp = int64(GetFileTimeNow());
    switch (completionStatus->value()) {
        case 4: {
            // Complete (courier delivery — validated via crate / end station)
            // First, we need to make sure that the container is indeed located in the end station
            if (call.client->GetStationID() != endStationID) {
                call.client->SendNotifyMsg("You have to deliver the package to %s", sItemFactory.GetStationRef(endStationID)->name());
                return new PyBool(false);
            }
            if (acceptorCharID != 0 && call.client->GetCharacterID() != acceptorCharID) {
                call.client->SendNotifyMsg("You are not the courier assigned to this contract.");
                return new PyBool(false);
            }
            if (!ValidateCorpCourierAcceptSession(call.client, acceptorWalletKeyRaw, acceptorCorpIDPersisted))
                return new PyBool(false);
            // Then, we validate the presence of all expected items
            std::map<int, int> expectedItems;
            ContractUtils::GetContractItemIDsAndQuantities(contractID->value(), &expectedItems);
            bool allItemsPresent(true);
            for (const auto& entry : expectedItems) {
                InventoryItemRef item = sItemFactory.GetItemRef(entry.first);
                if (item.get()) {
                    if (item->quantity() == entry.second && item->locationID() == crateID) {
                        continue;
                    }
                }
                allItemsPresent = false;
            }

            if (allItemsPresent) {
                // Once checks have passed, we extract the items into issuer inventory (character or corporation).
                for (const auto& entry : expectedItems) {
                    InventoryItemRef item = sItemFactory.GetItemRef(entry.first);
                    item->ChangeOwner(issuerWalletID, true);
                    item->Move(endStationID, flagHangar, true);
                }
                // Plastic wrap seems to self-destruct after all the items are removed from it, so there's no need to delete it.

                // Return escrowed collateral: pilot wallet (historic AddBalance) or corp ledger refund via SCC when acceptance persisted acceptorWalletKey.
                if (collateral > 0) {
                    if (acceptorWalletKeyRaw != 0) {
                        const uint16 acceptorDivision = static_cast<uint16>(acceptorWalletKeyRaw);
                        AccountService::TransferFunds(
                            corpSCC,
                            acceptorCorpIDPersisted,
                            static_cast<double>(collateral),
                            "Courier contract collateral return",
                            Journal::EntryType::ContractCollateralRefund,
                            contractID->value(),
                            Account::KeyType::Cash,
                            acceptorDivision,
                            call.client
                        );
                    } else {
                        call.client->AddBalance(collateral);
                    }
                }
                // Pay reward: personal issuer still debits issuer wallet at completion; corp issuer pays from SCC pool
                // funded at create (corp division → SCC), matching corp collateral symmetry.
                if (reward > 0) {
                    const uint32 rewardFromID = issuerForCorp ? corpSCC : issuerWalletID;
                    const uint16 rewardFromKey = issuerForCorp ? Account::KeyType::Cash : issuerMoneyKey;
                    if (acceptorCorpIDPersisted != 0u && acceptorWalletKeyRaw != 0) {
                        const uint16 acceptorRewardKey = static_cast<uint16>(acceptorWalletKeyRaw);
                        AccountService::TransferFunds(
                            rewardFromID,
                            acceptorCorpIDPersisted,
                            static_cast<double>(reward),
                            "Courier contract reward",
                            Journal::EntryType::ContractReward,
                            contractID->value(),
                            rewardFromKey,
                            acceptorRewardKey,
                            call.client
                        );
                    } else {
                        AccountService::TransferFunds(
                            rewardFromID,
                            call.client->GetCharacterID(),
                            static_cast<double>(reward),
                            "Courier contract reward",
                            Journal::EntryType::ContractReward,
                            contractID->value(),
                            rewardFromKey,
                            Account::KeyType::Cash,
                            call.client
                        );
                    }
                }

                // Then, we update the contract as Completed.
                DBerror err;
                if (!sDatabase.RunQuery(err,
                                        "UPDATE ctrContracts SET status = %u, dateCompleted = %lli WHERE contractId = %u",
                                        completionStatus->value(), timestamp, contractID->value()))
                {
                    codelog(DATABASE__ERROR, "Failed to update contract : %s", err.c_str());
                }
            } else {
                call.client->SendNotifyMsg("Not all required items are located in the container");
                return new PyBool(false);
            }
            break;
        }
        case 7: {
            // Fail — collateral flows to issuer (character or corp wallet division).
            if (acceptorCharID != 0 && call.client->GetCharacterID() != acceptorCharID) {
                call.client->SendNotifyMsg("You are not the courier assigned to this contract.");
                return new PyBool(false);
            }
            if (!ValidateCorpCourierAcceptSession(call.client, acceptorWalletKeyRaw, acceptorCorpIDPersisted))
                return new PyBool(false);
            if (collateral > 0) {
                if (acceptorWalletKeyRaw != 0) {
                    const uint16 acceptorDivision = static_cast<uint16>(acceptorWalletKeyRaw);
                    AccountService::TransferFunds(
                        corpSCC,
                        acceptorCorpIDPersisted,
                        static_cast<double>(collateral),
                        "Courier contract collateral release before forfeiture",
                        Journal::EntryType::ContractCollateralRefund,
                        contractID->value(),
                        Account::KeyType::Cash,
                        acceptorDivision,
                        call.client
                    );
                    AccountService::TransferFunds(
                        acceptorCorpIDPersisted,
                        issuerWalletID,
                        static_cast<double>(collateral),
                        "Collateral payment for failed contract",
                        Journal::EntryType::ContractCollateral,
                        contractID->value(),
                        acceptorDivision,
                        issuerMoneyKey,
                        call.client
                    );
                } else {
                    call.client->AddBalance(collateral);
                    AccountService::TransferFunds(
                        call.client->GetCharacterID(),
                        issuerWalletID,
                        static_cast<double>(collateral),
                        "Collateral payment for failed contract",
                        Journal::EntryType::ContractCollateral,
                        contractID->value(),
                        Account::KeyType::Cash,
                        issuerMoneyKey,
                        call.client
                    );
                }
            }
            // Corp courier reward was escrowed issuer corp → SCC at create; return it on failed delivery.
            if (contractType == 3 && reward > 0 && issuerForCorp) {
                AccountService::TransferFunds(
                    corpSCC,
                    issuerWalletID,
                    static_cast<double>(reward),
                    "Courier contract reward refund on failure",
                    Journal::EntryType::ContractCollateralRefund,
                    contractID->value(),
                    Account::KeyType::Cash,
                    issuerMoneyKey,
                    call.client
                );
            }
            // Then, we update the contract as failed.
            DBerror err;
            if (!sDatabase.RunQuery(err,
                                    "UPDATE ctrContracts SET status = %u, dateCompleted = %lli WHERE contractId = %u",
                                    completionStatus->value(), timestamp, contractID->value()))
            {
                codelog(DATABASE__ERROR, "Failed to update contract : %s", err.c_str());
            }
            break;
        }
        default:
            codelog(SERVICE__ERROR, "CompleteContract: unsupported completionStatus=%i contractType=%i contractID=%u",
                    completionStatus->value(), contractType, contractID->value());
            return new PyBool(false);
    }

    return new PyBool(true);
}


PyResult ContractProxy::GetMyExpiredContractList(PyCallArgs &call) {
  sLog.White( "ContractProxy::Handle_GetMyExpiredContractList()", "size=%lu", call.tuple->size());
    call.Dump(SERVICE__CALL_DUMP);
/*
      [PySubStream 530 bytes]
        [PyObjectData Name: util.KeyVal]
          [PyDict 3 kvp]
            [PyString "contracts"]
            [PyObjectEx Type2]
              [PyTuple 2 items]
                [PyTuple 1 items]
                  [PyToken dbutil.CRowset]
                [PyDict 1 kvp]
                  [PyString "header"]
                  [PyObjectEx Normal]
                    [PyTuple 2 items]
                      [PyToken blue.DBRowDescriptor]
                      [PyTuple 1 items]
                        [PyTuple 28 items]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "type"]
                            [PyInt 17]
                          [PyTuple 2 items]
                            [PyString "issuerID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "issuerCorpID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "forCorp"]
                            [PyInt 11]
                          [PyTuple 2 items]
                            [PyString "availability"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "assigneeID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "dateIssued"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "dateExpired"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "dateAccepted"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "numDays"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "dateCompleted"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "startStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "startSolarSystemID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "startRegionID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endSolarSystemID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endRegionID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "price"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "reward"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "collateral"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "title"]
                            [PyInt 130]
                          [PyTuple 2 items]
                            [PyString "status"]
                            [PyInt 17]
                          [PyTuple 2 items]
                            [PyString "volume"]
                            [PyInt 5]
                          [PyTuple 2 items]
                            [PyString "issuerAllianceID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "issuerWalletKey"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorWalletKey"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorCorpID"]
                            [PyInt 3]
            [PyString "items"]
            [PyDict 0 kvp]
            [PyString "bids"]
            [PyDict 0 kvp]
            */
    return nullptr;
}

PyResult ContractProxy::NumOutstandingContracts(PyCallArgs &call) {
    sLog.White( "ContractProxy::Handle_NumOutstandingContracts()", "size=%lu", call.tuple->size());
    call.Dump(SERVICE__CALL_DUMP);
    /*
      [PySubStream 87 bytes]
        [PyObjectData Name: util.KeyVal]
          [PyDict 4 kvp]
            [PyString "nonCorpForMyChar"]
            [PyInt 0]
            [PyString "myCorpTotal"]
            [PyInt 0]
            [PyString "nonCorpForMyCorp"]
            [PyInt 0]
            [PyString "myCharTotal"]
            [PyInt 0]
            */
    return nullptr;
}

PyResult ContractProxy::GetItemsInStation(PyCallArgs &call, PyInt* stationID, std::optional<PyInt*> forCorp) {
    if (call.client == nullptr || stationID == nullptr) {
        codelog(SERVICE__ERROR, "GetItemsInStation: null client or stationID");
        return nullptr;
    }

    const uint32 sid = stationID->value();

    if (call.tuple != nullptr && call.tuple->size() > 0) {
        PyRep* const r0 = call.tuple->GetItem(0);
        if (r0 != nullptr && r0->IsInt()) {
            const uint32 tupleSid = r0->AsInt()->value();
            if (tupleSid != sid)
                codelog(SERVICE__ERROR, "GetItemsInStation: tuple[0] station %u != bound stationID %u (using bound id)", tupleSid, sid);
        }
    }

    if (!sDataMgr.IsStation(sid)) {
        codelog(SERVICE__ERROR, "GetItemsInStation: id %u is not a station", sid);
        return nullptr;
    }

    StationItemRef sref = sItemFactory.GetStationRef(sid);
    if (!sref) {
        codelog(SERVICE__ERROR, "GetItemsInStation: GetStationRef(%u) returned null", sid);
        return nullptr;
    }

    Inventory* inv = sref->GetMyInventory();
    if (inv == nullptr) {
        codelog(SERVICE__ERROR, "GetItemsInStation: station %u has null inventory", sid);
        return nullptr;
    }

    uint32 itemOwner = call.client->GetCharacterID();
    if (forCorp.has_value() && forCorp.value() != nullptr && forCorp.value()->value() != 0)
        itemOwner = call.client->GetCorporationID();

    sLog.White("ContractProxy::GetItemsInStation()", "station=%u itemOwner=%u forCorpOpt=%d", sid, itemOwner, forCorp.has_value() ? 1 : 0);

    return inv->List(flagHangar, itemOwner);
}

PyResult ContractProxy::CollectMyPageInfo(PyCallArgs &call) {
    sLog.White( "ContractProxy::Handle_CollectMyPageInfo()", "size=%lu", call.tuple->size());
    call.Dump(SERVICE__CALL_DUMP);
    std::string mainQuery = "SELECT "
                            "IFNULL(SUM(CASE WHEN (cC.issuerID = {CHAR_ID} AND cC.status = 0) THEN 1 ELSE 0 END), 0) AS numOutstandingContracts, "
                            "IFNULL(SUM(CASE WHEN (cC.issuerID = {CHAR_ID} AND cC.status = 0 AND cC.forCorp = false) THEN 1 ELSE 0 END), 0) AS numOutstandingContractsNonCorp, "
                            "IFNULL(SUM(CASE WHEN (cC.issuerID = {CHAR_ID} AND cC.status = 0 AND cC.forCorp = true) THEN 1 ELSE 0 END), 0) AS numOutstandingContractsForCorp, "
                            "IFNULL(SUM(CASE WHEN (cC.assigneeID = {CHAR_ID} AND cC.forCorp = false AND cC.status = 1) THEN 1 ELSE 0 END), 0) AS numInProgress, "
                            "IFNULL(SUM(CASE WHEN (cC.issuerCorpID = {CORP_ID} AND cC.forCorp = true AND cC.status = 1) THEN 1 ELSE 0 END), 0) AS numInProgressCorp, "
                            "IFNULL(SUM(CASE WHEN (cC.assigneeID = {CHAR_ID} AND cC.status = 1) THEN 1 ELSE 0 END), 0) AS numRequiresAttention, "
                            "IFNULL(SUM(CASE WHEN (cC.issuerCorpID = {CORP_ID} AND cC.forCorp = true AND cC.status = 1) THEN 1 ELSE 0 END), 0) AS numRequiresAttentionCorp "
                            "FROM ctrContracts cC "
                            "LEFT JOIN ctrBids cB on cC.contractId = cB.contractId";
    std::string outstandingContractsQuery = "SELECT issuerID, issuerCorpID, assigneeID, contractType "
                                            "FROM ctrContracts "
                                            "WHERE assigneeID IN ({CHAR_ID},{CORP_ID}) and status = 0";
    // Since we already use boost - why not use some of it's libraries for string juggling? :P
    boost::replace_all(mainQuery, "{CHAR_ID}", std::to_string(call.client->GetCharacterID()));
    boost::replace_all(mainQuery, "{CORP_ID}", std::to_string(call.client->GetCorporationID()));
    boost::replace_all(outstandingContractsQuery, "{CHAR_ID}", std::to_string(call.client->GetCharacterID()));
    boost::replace_all(outstandingContractsQuery, "{CORP_ID}", std::to_string(call.client->GetCorporationID()));

    // First, we gather outstanding contracts - they will later be packed into response dict
    DBQueryResult res;
    if (!sDatabase.RunQuery(res, outstandingContractsQuery.c_str()))
    {
        codelog(DATABASE__ERROR, "Error in outstandingContractsQuery: %s", res.error.c_str());
        return nullptr;
    }
    DBResultRow row;
    PyList* oustandingContractsList = new PyList;
    while (res.GetRow(row)) {
        PyList* list = new PyList(4);
        list->SetItem(0, new PyInt(row.GetInt(0)));
        list->SetItem(1, new PyInt(row.GetInt(1)));
        list->SetItem(2, new PyInt(row.GetInt(2)));
        list->SetItem(3, new PyInt(row.GetInt(3)));

        oustandingContractsList->AddItem(list);
    }

    // Then, we go for main message body data
    if (!sDatabase.RunQuery(res, mainQuery.c_str()))
    {
        codelog(DATABASE__ERROR, "Error in mainQuery: %s", res.error.c_str());
        return nullptr;
    }
    // Because of outstandingContracts list in this response, we can't return DBResultToCRowset directly - so, we'll have to compose the dict manually.
    res.GetRow(row);
    PyDict* vals = new PyDict;
    vals->SetItemString("numOutstandingContracts", new PyInt(row.GetInt(0)));
    vals->SetItemString("numOutstandingContractsNonCorp", new PyInt(row.GetInt(1)));
    vals->SetItemString("numOutstandingContractsForCorp", new PyInt(row.GetInt(2)));
    vals->SetItemString("numInProgress", new PyInt(row.GetInt(3)));
    vals->SetItemString("numInProgressCorp", new PyInt(row.GetInt(4)));
    vals->SetItemString("outstandingContracts", oustandingContractsList);
    vals->SetItemString("numRequiresAttention", new PyInt(row.GetInt(5)));
    vals->SetItemString("numRequiresAttentionCorp", new PyInt(row.GetInt(6)));
    vals->SetItemString("numBiddingOn", new PyInt(0));      // Left hard-coded until bidding is implemented
    vals->SetItemString("numBiddingOnCorp", new PyInt(0));  // Left hard-coded until bidding is implemented

    return new PyObject("util.KeyVal", vals);
}

PyResult ContractProxy::GetContractListForOwner(PyCallArgs &call, PyInt* ownerID, PyInt* contractStatus, std::optional <PyInt*> contractType, std::optional <PyBool*> issuedToBy) {
    sLog.White( "ContractProxy::Handle_GetContractListForOwner()", "size=%lu", call.tuple->size());
    call.Dump(SERVICE__CALL_DUMP);

    return ContractUtils::GetContractListForOwner(ownerID, contractStatus, contractType, issuedToBy);
    /*
     *  client call....
      [PyTuple 2 items]
        [PyInt 0]
        [PySubStream 73 bytes]
          [PyTuple 4 items]
            [PyInt 1]
            [PyString "GetContractListForOwner"]
            [PyTuple 4 items]
              [PyInt 649670823]
              [PyInt 0] (Contract status, 0 for outstanding, 1 for in progress, 4 for Finished)
              [PyInt] (Contract type. 1 for exchange, 2 for auction, 3 for courier, None for all)
              [PyBool] (false for Issued By, true for issued To, None for both)
            [PyDict 3 kvp]
              [PyString "num"]
              [PyInt 100]
              [PyString "machoVersion"]
              [PyInt 1]
              [PyString "startContractID"]
              [PyNone]

        server reply...
      [PySubStream 713 bytes]
        [PyObjectData Name: util.KeyVal]
          [PyDict 3 kvp]
            [PyString "contracts"]
            [PyObjectEx Type2]
              [PyTuple 2 items]
                [PyTuple 1 items]
                  [PyToken dbutil.CRowset]
                [PyDict 1 kvp]
                  [PyString "header"]
                  [PyObjectEx Normal]
                    [PyTuple 2 items]
                      [PyToken blue.DBRowDescriptor]
                      [PyTuple 1 items]
                        [PyTuple 30 items]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "type"]
                            [PyInt 17]
                          [PyTuple 2 items]
                            [PyString "issuerID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "issuerCorpID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "forCorp"]
                            [PyInt 11]
                          [PyTuple 2 items]
                            [PyString "availability"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "assigneeID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "dateIssued"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "dateExpired"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "dateAccepted"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "numDays"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "dateCompleted"]
                            [PyInt 64]
                          [PyTuple 2 items]
                            [PyString "startStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "startSolarSystemID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "startRegionID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endSolarSystemID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endRegionID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "price"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "reward"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "collateral"]
                            [PyInt 6]
                          [PyTuple 2 items]
                            [PyString "title"]
                            [PyInt 130]
                          [PyTuple 2 items]
                            [PyString "status"]
                            [PyInt 17]
                          [PyTuple 2 items]
                            [PyString "volume"]
                            [PyInt 5]
                          [PyTuple 2 items]
                            [PyString "issuerAllianceID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "issuerWalletKey"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorWalletKey"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "acceptorCorpID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "crateID"]
                            [PyInt 20]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
              [PyPackedRow 146 bytes]
                ["contractID" => <41239648> [I4]]
                ["type" => <1> [UI1]]
                ["issuerID" => <649670823> [I4]]
                ["issuerCorpID" => <98038978> [I4]]
                ["forCorp" => <0> [Bool]]
                ["availability" => <1> [I4]]
                ["assigneeID" => <1661059544> [I4]]
                ["acceptorID" => <0> [I4]]
                ["dateIssued" => <129494707760000000> [FileTime]]
                ["dateExpired" => <129495571760000000> [FileTime]]
                ["dateAccepted" => <129494707760000000> [FileTime]]
                ["numDays" => <0> [I4]]
                ["dateCompleted" => <129494707760000000> [FileTime]]
                ["startStationID" => <60006433> [I4]]
                ["startSolarSystemID" => <30000135> [I4]]
                ["startRegionID" => <10000002> [I4]]
                ["endStationID" => <60006433> [I4]]
                ["endSolarSystemID" => <0> [I4]]
                ["endRegionID" => <0> [I4]]
                ["price" => <150000000> [CY]]
                ["reward" => <0> [CY]]
                ["collateral" => <0> [CY]]
                ["title" => <quafe!> [WStr]]
                ["status" => <0> [UI1]]
                ["volume" => <6> [R8]]
                ["issuerAllianceID" => <0> [I4]]
                ["issuerWalletKey" => <0> [I4]]
                ["acceptorWalletKey" => <0> [I4]]
                ["acceptorCorpID" => <0> [I4]]
                ["crateID" => <1002309425092> [I8]]
                ["contractID" => <41239648> [I4]]
            [PyString "items"]
            [PyDict 1 kvp]
              [PyInt 41239648]
              [PyList 1 items]
                [PyObjectData Name: util.Row]
                  [PyDict 2 kvp]
                    [PyString "header"]
                    [PyList 3 items]
                      [PyString "itemTypeID"]
                      [PyString "quantity"]
                      [PyString "inCrate"]
                    [PyString "line"]
                    [PyList 3 items]
                      [PyInt 3898]
                      [PyInt 6]
                      [PyBool True]
            [PyString "bids"]
            [PyDict 0 kvp]
     */
    return nullptr;
}

PyResult ContractProxy::GetLoginInfo(PyCallArgs &call)
{
    // currently a stub as I need to redesign or change some sub systems for this.

    /* create needsAttention row descriptor */
    DBRowDescriptor *needsAttentionHeader = new DBRowDescriptor();
        needsAttentionHeader->AddColumn( "contractID",   DBTYPE_I4);
        needsAttentionHeader->AddColumn( "",             DBTYPE_I4);

    /* create inProgress row descriptor */
    DBRowDescriptor *inProgressHeader = new DBRowDescriptor();
        inProgressHeader->AddColumn( "contractID",      DBTYPE_I4 );
        inProgressHeader->AddColumn( "startStationID",  DBTYPE_I4 );
        inProgressHeader->AddColumn( "endStationID",    DBTYPE_I4 );
        inProgressHeader->AddColumn( "expires",         DBTYPE_FILETIME );

    /* create assignedToMe row descriptor */
    DBRowDescriptor *assignedToMeHeader = new DBRowDescriptor();
        assignedToMeHeader->AddColumn( "contractID",    DBTYPE_I4);
        assignedToMeHeader->AddColumn( "issuerID",      DBTYPE_I4);

    CRowSet *needsAttention_rowset = new CRowSet( &needsAttentionHeader );
    CRowSet *inProgress_rowset = new CRowSet( &inProgressHeader );
    CRowSet *assignedToMe_rowset = new CRowSet( &assignedToMeHeader );

    PyDict* args = new PyDict;
        args->SetItemString( "needsAttention",          needsAttention_rowset );
        args->SetItemString( "inProgress",              inProgress_rowset );
        args->SetItemString( "assignedToMe",            assignedToMe_rowset );

    return new PyObject( "util.KeyVal", args );
}

     /**
     * NOTE: Contract statuses:
     * 0 - Outstanding
     * 1 - In Progress
     * 2 - Items not yet claimed
     * 3 - Unclaimed by seller
     * 4,5 - Finished
     * 6 - Rejected
     * 7 - Failed
     * 8 - Deleted
     * 9 - Reversal
     */

/* Description
 * GetLoginInfo sends back a util.KeyVal PyClass. This class contains 3 entries, those entries are
 * "needsAttention", "inProgress" and "assignedToMe".
 *
 * ------------------
 * assignedToMe
 * ------------------
 * assignedToMe is a pretty obvious packet, it contains rows of userid's and contractid's
 * that are belonging to the player.
 *
 * ------------------
 * inProgress
 * ------------------
 * inProgress is also pretty obvious, it contains rows of contractID, startStationID, endStationID and expires
 * that marks what contract is in progress.
 *
 * ------------------
 * needsAttention
 * ------------------
 * needsAttention contains contracts that need attention, its rather a way to make the journal blink. The
 * contracts off course are highlighted in the journal.
 *
      [PySubStream 273 bytes]
        [PyObjectData Name: util.KeyVal]
          [PyDict 3 kvp]
            [PyString "inProgress"]
            [PyObjectEx Type2]
              [PyTuple 2 items]
                [PyTuple 1 items]
                  [PyToken dbutil.CRowset]
                [PyDict 1 kvp]
                  [PyString "header"]
                  [PyObjectEx Normal]
                    [PyTuple 2 items]
                      [PyToken blue.DBRowDescriptor]
                      [PyTuple 1 items]
                        [PyTuple 4 items]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "startStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "endStationID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "expires"]
                            [PyInt 64]
            [PyString "needsAttention"]
            [PyObjectEx Type2]
              [PyTuple 2 items]
                [PyTuple 1 items]
                  [PyToken dbutil.CRowset]
                [PyDict 1 kvp]
                  [PyString "header"]
                  [PyObjectEx Normal]
                    [PyTuple 2 items]
                      [PyToken blue.DBRowDescriptor]
                      [PyTuple 1 items]
                        [PyTuple 2 items]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString ""]
                            [PyInt 3]
            [PyString "assignedToMe"]
            [PyObjectEx Type2]
              [PyTuple 2 items]
                [PyTuple 1 items]
                  [PyToken dbutil.CRowset]
                [PyDict 1 kvp]
                  [PyString "header"]
                  [PyObjectEx Normal]
                    [PyTuple 2 items]
                      [PyToken blue.DBRowDescriptor]
                      [PyTuple 1 items]
                        [PyTuple 2 items]
                          [PyTuple 2 items]
                            [PyString "contractID"]
                            [PyInt 3]
                          [PyTuple 2 items]
                            [PyString "issuerID"]
                            [PyInt 3]
*/
