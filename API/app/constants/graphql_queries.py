from __future__ import annotations

SELECTION_SET_VERSION = "default-v1"

SHORT_LINK_SELECTION_SET = "shortLink"

PRODUCT_OFFER_V2_SELECTION_SET = """
nodes{
itemId
commissionRate
sellerCommissionRate
shopeeCommissionRate
commission
sales
priceMax
priceMin
productCatIds
ratingStar
priceDiscountRate
imageUrl
productName
shopId
shopName
shopType
productLink
offerLink
periodStartTime
periodEndTime
}
pageInfo{
limit
hasNextPage
scrollId
}
""".strip()

SHOP_OFFER_V2_SELECTION_SET = """
nodes{
commissionRate
imageUrl
offerLink
originalLink
shopId
shopName
ratingStar
shopType
remainingBudget
periodStartTime
periodEndTime
sellerCommCoveRatio
}
pageInfo{
limit
hasNextPage
scrollId
}
""".strip()

