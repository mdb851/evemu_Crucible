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
    Foundation, either version 2 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License along with
    this program; if not, write to the Free Software Foundation, Inc., 59 Temple
    Place - Suite 330, Boston, MA 02111-1307, USA, or go to
    http://www.gnu.org/copyleft/lesser.txt.
    ------------------------------------------------------------------------------------
*/

#include "eve-test.h"

#include "account/AccountDB.h"
#include "contract/ContractUtils.h"

int server_ServerLinkSmokeTest( int argc, char* argv[] )
{
    (void)argc;
    (void)argv;

    /* Pull symbols from eve-server-testlib without running DB-backed code paths. */
    volatile auto pXfer = &AccountDB::OfflineFundXfer;
    volatile auto pContract = &ContractUtils::GetContractEntry;
    (void)pXfer;
    (void)pContract;

    return EXIT_SUCCESS;
}
