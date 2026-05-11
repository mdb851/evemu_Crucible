/*
    ------------------------------------------------------------------------------------
    LICENSE:
    ------------------------------------------------------------------------------------
    This file is part of EVEmu: EVE Online Server Emulator
    Copyright 2006 - 2011 The EVEmu Team
    For the latest information visit http://evemu.org
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
    Author:        Zhur
    Rewrite:    Allan
*/

/*
 * AgentMgr bound(agentID):
 *  -> DoAction(actionID or None)
 *  -> WarpToLocation(locationType, locationNumber, warpRange, is_gang)
 *
 *   Also sent an OnRemoteMessage(AgtMissionOfferWarning)
 *
 *   and various OnAgentMissionChange()
 *
*/

/*
 * # Agent Logging:
 * AGENT__ERROR
 * AGENT__WARNING
 * AGENT__MESSAGE
 * AGENT__DEBUG
 * AGENT__INFO
 * AGENT__TRACE
 * AGENT__DUMP
 * AGENT__RSP_DUMP
 */

#include "eve-server.h"

#include "EntityList.h"
#include "StaticDataMgr.h"
#include "agents/Agent.h"
#include "agents/AgentBound.h"
#include "agents/AgentMgrService.h"
#include "missions/MissionDataMgr.h"
#include "services/ServiceManager.h"

AgentMgrService::AgentMgrService(EVEServiceManager& mgr) :
    BindableService("agentMgr", mgr)
{
    this->Add("GetAgents", &AgentMgrService::GetAgents);
    this->Add("GetCareerAgents", &AgentMgrService::GetCareerAgents);
    this->Add("GetMyJournalDetails", &AgentMgrService::GetMyJournalDetails);
    this->Add("GetSolarSystemOfAgent", &AgentMgrService::GetSolarSystemOfAgent);
    this->Add("GetMyEpicJournalDetails", &AgentMgrService::GetMyEpicJournalDetails);
}

BoundDispatcher* AgentMgrService::BindObject(Client* client, PyRep* bindParameters) {
    _log(AGENT__ERROR, "AGENT_BIND_1_ENTRY: client=%p, bindParameters=%p", client, bindParameters);
    
    if (client == nullptr) {
        _log(AGENT__ERROR, "AGENT_BIND_2_CLIENT_NULL");
        return nullptr;
    }
    
    _log(AGENT__ERROR, "AGENT_BIND_3_CLIENT_OK");
    
    if (!bindParameters->IsInt()) {
        _log(AGENT__ERROR, "AGENT_BIND_4_BINDPARAM_NOT_INT: type=%s", bindParameters->TypeString());
        return nullptr;
    }

    _log(AGENT__ERROR, "AGENT_BIND_5_BINDPARAM_IS_INT");
    
    uint32 agentID = bindParameters->AsInt()->value();
    
    _log(AGENT__ERROR, "AGENT_BIND_6_AGENT_ID_EXTRACTED: agentID=%u", agentID);
    
    Agent* pAgent = sEntityList.GetAgent(agentID);

    _log(AGENT__ERROR, "AGENT_BIND_7_ENTITY_LOOKUP_DONE: pAgent=%p, agentID=%u", pAgent, agentID);

    if (pAgent == nullptr) {
        _log(AGENT__ERROR, "AGENT_BIND_8_AGENT_NULL");
        return nullptr;
    }
    
    _log(AGENT__ERROR, "AGENT_BIND_9_AGENT_FOUND");

    auto it = this->m_instances.find (agentID);

    _log(AGENT__ERROR, "AGENT_BIND_10_CACHE_LOOKUP_DONE: found=%d", (it != this->m_instances.end()) ? 1 : 0);

    if (it != this->m_instances.end ()) {
        _log(AGENT__ERROR, "AGENT_BIND_11_CACHE_HIT: returning cached bound=%p", it->second);
        return it->second;
    }

    _log(AGENT__ERROR, "AGENT_BIND_12_CACHE_MISS: about_to_new_AgentBound");
    
    AgentBound* bound = new AgentBound(this->GetServiceManager(), *this, pAgent);
    
    _log(AGENT__ERROR, "AGENT_BIND_13_NEW_AGENTBOUND_DONE: bound=%p", bound);

    this->m_instances.insert_or_assign (agentID, bound);

    _log(AGENT__ERROR, "AGENT_BIND_14_INSERT_DONE: returning bound=%p", bound);

    return bound;
}

void AgentMgrService::BoundReleased (AgentBound* bound) {
    auto it = this->m_instances.find (bound->GetAgent()->GetID());

    if (it == this->m_instances.end ())
        return;

    this->m_instances.erase (it);
}

PyResult AgentMgrService::GetAgents(PyCallArgs &call) {
    // this is cached on client side...
    return sDataMgr.GetAgents();
}

PyResult AgentMgrService::GetSolarSystemOfAgent(PyCallArgs &call, PyInt* agentID)
{
    return sDataMgr.GetAgentSystemID(agentID->value());
}

PyResult AgentMgrService::GetMyJournalDetails(PyCallArgs &call) {
// note:  this will show mission data in journal AND "offered" msg in agent data bloc on agent tab in station

    _log(AGENT__INFO, "AgentMgrService::Handle_GetMyJournalDetails() - size=%lli", call.tuple->size());
    call.Dump(AGENT__DUMP);

    PyTuple *tuple = new PyTuple(2);
    //missions:
    PyList* missions = new PyList();
    std::vector<MissionOffer> data;
    sMissionDataMgr.LoadMissionOffers(call.client->GetCharacterID(), data);
    for (auto cur : data) {
        PyTuple* mData = new PyTuple(9);
        mData->SetItem(0, new PyInt(cur.stateID));
        mData->SetItem(1, new PyInt(cur.important?1:0));
        mData->SetItem(2, new PyString(sMissionDataMgr.GetTypeLabel(cur.typeID)));
        mData->SetItem(3, new PyString(cur.name));
        mData->SetItem(4, new PyInt(cur.agentID));
        mData->SetItem(5, new PyLong(cur.expiryTime));
        mData->SetItem(6, cur.bookmarks->Clone());
        mData->SetItem(7, new PyBool(cur.remoteOfferable));
        mData->SetItem(8, new PyBool(cur.remoteCompletable));
        missions->AddItem(mData);
    }
    tuple->SetItem(0, missions);

    //research:
    PyList* research = new PyList();
    tuple->SetItem(1, research);

    if (is_log_enabled(AGENT__RSP_DUMP))
        tuple->Dump(AGENT__RSP_DUMP, "   ");
    return tuple;
}

PyResult AgentMgrService::GetMyEpicJournalDetails(PyCallArgs& call)
{
    _log(AGENT__INFO, "AgentMgrBound::Handle_GetMyEpicJournalDetails() - size=%lli", call.tuple->size());
    return new PyList();
}

PyResult AgentMgrService::GetCareerAgents(PyCallArgs &call)
{
    _log(AGENT__INFO, "AgentMgrBound::Handle_GetCareerAgents() - size=%lli", call.tuple->size());
    call.Dump(AGENT__DUMP);
    return PyStatic.NewZero();
}

EpicArcService::EpicArcService() :
    Service("epicArcStatus")
{
    this->Add("AgentHasEpicMissionsForCharacter", &EpicArcService::AgentHasEpicMissionsForCharacter);
}

PyResult EpicArcService::AgentHasEpicMissionsForCharacter(PyCallArgs &call, PyInt* agentID) {
    _log(AGENT__INFO, "EpicArcService::Handle_AgentHasEpicMissionsForCharacter() - size=%lli", call.tuple->size());
    call.Dump(AGENT__DUMP);
    return PyStatic.NewFalse();
}
