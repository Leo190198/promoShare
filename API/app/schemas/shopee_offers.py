from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


class PageInfo(BaseModel):
    limit: int | None = None
    hasNextPage: bool | None = None
    scrollId: str | None = None


class ProductOfferV2Node(BaseModel):
    itemId: int | None = None
    commissionRate: str | None = None
    sellerCommissionRate: str | None = None
    shopeeCommissionRate: str | None = None
    commission: str | None = None
    sales: int | None = None
    priceMax: str | None = None
    priceMin: str | None = None
    productCatIds: list[int] | None = None
    ratingStar: str | None = None
    priceDiscountRate: int | None = None
    imageUrl: str | None = None
    productName: str | None = None
    shopId: int | None = None
    shopName: str | None = None
    shopType: list[int] | None = None
    productLink: str | None = None
    offerLink: str | None = None
    periodStartTime: int | None = None
    periodEndTime: int | None = None


class ProductOfferSearchData(BaseModel):
    nodes: list[ProductOfferV2Node]
    pageInfo: PageInfo


class ProductFromUrlRequest(BaseModel):
    url: AnyHttpUrl


class ProductFromUrlData(BaseModel):
    shopId: int
    itemId: int
    productName: str | None = None
    imageUrl: str | None = None
    priceMin: str | None = None
    priceMax: str | None = None
    offerLink: str | None = None
    productLink: str | None = None
    shopName: str | None = None
    commissionRate: str | None = None


class ShopOfferV2Node(BaseModel):
    commissionRate: str | None = None
    imageUrl: str | None = None
    offerLink: str | None = None
    originalLink: str | None = None
    shopId: int | None = None
    shopName: str | None = None
    ratingStar: str | None = None
    shopType: list[int] | None = None
    remainingBudget: int | None = None
    periodStartTime: int | None = None
    periodEndTime: int | None = None
    sellerCommCoveRatio: str | None = None


class ShopOfferSearchData(BaseModel):
    nodes: list[ShopOfferV2Node]
    pageInfo: PageInfo


class ProductOffersSearchRequest(BaseModel):
    shopId: int | None = None
    itemId: int | None = None
    productCatId: int | None = None
    listType: Literal[0, 1, 2, 3, 4, 5, 6] | None = None
    matchId: int | None = None
    keyword: str | None = None
    sortType: Literal[1, 2, 3, 4, 5] | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    isAMSOffer: bool | None = None
    isKeySeller: bool | None = None

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def validate_filter_combinations(self) -> "ProductOffersSearchRequest":
        has_list_mode = self.listType is not None or self.matchId is not None

        if self.matchId is not None and self.listType is None:
            raise ValueError("matchId requires listType")

        if has_list_mode:
            conflicting = [
                ("shopId", self.shopId),
                ("itemId", self.itemId),
                ("productCatId", self.productCatId),
                ("keyword", self.keyword),
                ("sortType", self.sortType),
                ("isAMSOffer", self.isAMSOffer),
                ("isKeySeller", self.isKeySeller),
            ]
            used_conflicts = [name for name, value in conflicting if value is not None]
            if used_conflicts:
                raise ValueError(
                    "listType/matchId cannot be combined with filters: " + ", ".join(used_conflicts)
                )
        return self


class ShopOffersSearchRequest(BaseModel):
    shopId: int | None = None
    keyword: str | None = None
    shopType: list[int] | None = None
    isKeySeller: bool | None = None
    sortType: Literal[1, 2, 3] | None = None
    sellerCommCoveRatio: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("shopType")
    @classmethod
    def validate_shop_type(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        allowed = {1, 2, 4}
        invalid = [item for item in value if item not in allowed]
        if invalid:
            raise ValueError("shopType items must be one of 1, 2, 4")
        return value
