-- Tier B — post-client checks for corporation market orders (after PlaceCharOrder / modify / cancel with isCorp).
-- `mktOrders.isCorp` / `accountKey` / `memberID` are populated by MarketDB::StoreOrder (see MarketProxyService).

SELECT orderID, typeID, ownerID, stationID, bid, price, volRemaining, isCorp, accountKey, memberID, issued
FROM mktOrders
WHERE isCorp = 1
ORDER BY orderID DESC
LIMIT 25;

SELECT COUNT(*) AS corp_market_order_rows
FROM mktOrders
WHERE isCorp = 1;
