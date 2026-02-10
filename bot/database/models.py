from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WriteOffReason(str, enum.Enum):
    DEFECT = "defect"  # Брак
    DAMAGE = "damage"  # Бракираж (повреждение)
    LOSS = "loss"  # Потеря
    OTHER = "other"  # Другое


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="user", lazy="selectin")
    sales: Mapped[List["Sale"]] = relationship(back_populates="sold_by_user", lazy="selectin")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or self.username or str(self.telegram_id)

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.OWNER)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    brands: Mapped[List["Brand"]] = relationship(back_populates="category", lazy="selectin")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="brands", lazy="selectin")
    products: Mapped[List["Product"]] = relationship(back_populates="brand", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(255))  # Вкус/название
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purchase_price: Mapped[float] = mapped_column(Float, default=0.0)  # Цена закупки
    sale_price: Mapped[float] = mapped_column(Float, default=0.0)  # Цена продажи
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # Остаток
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Telegram file_id
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand: Mapped["Brand"] = relationship(back_populates="products", lazy="selectin")
    supply_items: Mapped[List["SupplyItem"]] = relationship(back_populates="product", lazy="selectin")
    sales: Mapped[List["Sale"]] = relationship(back_populates="product", lazy="selectin")
    write_offs: Mapped[List["WriteOff"]] = relationship(back_populates="product", lazy="selectin")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="product", lazy="selectin")
    channel_posts: Mapped[List["ChannelPost"]] = relationship(back_populates="product", lazy="selectin")

    @property
    def full_name(self) -> str:
        return f"{self.brand.name} - {self.name}"

    @property
    def margin(self) -> float:
        """Calculate profit margin"""
        if self.purchase_price == 0:
            return 0
        return self.sale_price - self.purchase_price

    @property
    def margin_percent(self) -> float:
        """Calculate profit margin percentage"""
        if self.purchase_price == 0:
            return 0
        return ((self.sale_price - self.purchase_price) / self.purchase_price) * 100


class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    items: Mapped[List["SupplyItem"]] = relationship(back_populates="supply", lazy="selectin")


class SupplyItem(Base):
    __tablename__ = "supply_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    purchase_price: Mapped[float] = mapped_column(Float)  # Цена закупки на момент поставки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    supply: Mapped["Supply"] = relationship(back_populates="items", lazy="selectin")
    product: Mapped["Product"] = relationship(back_populates="supply_items", lazy="selectin")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    sale_price: Mapped[float] = mapped_column(Float)  # Цена продажи на момент сделки
    purchase_price: Mapped[float] = mapped_column(Float)  # Цена закупки на момент сделки (для расчета прибыли)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sold_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="sales", lazy="selectin")
    sold_by_user: Mapped[Optional["User"]] = relationship(back_populates="sales", lazy="selectin")

    @property
    def profit(self) -> float:
        return (self.sale_price - self.purchase_price) * self.quantity


class WriteOff(Base):
    __tablename__ = "write_offs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[WriteOffReason] = mapped_column(SQLEnum(WriteOffReason))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="write_offs", lazy="selectin")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ReservationStatus] = mapped_column(SQLEnum(ReservationStatus), default=ReservationStatus.ACTIVE)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="reservations", lazy="selectin")
    user: Mapped["User"] = relationship(back_populates="reservations", lazy="selectin")

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at and self.status == ReservationStatus.ACTIVE


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Logging toggles
    log_sales: Mapped[bool] = mapped_column(Boolean, default=True)
    log_supplies: Mapped[bool] = mapped_column(Boolean, default=True)
    log_writeoffs: Mapped[bool] = mapped_column(Boolean, default=True)
    log_products: Mapped[bool] = mapped_column(Boolean, default=True)
    log_reservations: Mapped[bool] = mapped_column(Boolean, default=True)

    # Reminder settings
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_hour: Mapped[int] = mapped_column(Integer, default=23)
    reminder_minute: Mapped[int] = mapped_column(Integer, default=0)

    # Stock settings
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=3)

    # Reservation settings
    reservation_hours: Mapped[int] = mapped_column(Integer, default=24)

    # Pricelist template settings
    pricelist_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    pricelist_show_quantities: Mapped[bool] = mapped_column(Boolean, default=True)
    pricelist_show_brands: Mapped[bool] = mapped_column(Boolean, default=True)
    pricelist_footer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    pricelist_photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)

    # Pricelist auto-publish settings
    pricelist_auto_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pricelist_auto_frequency: Mapped[int] = mapped_column(Integer, default=1)  # 1, 2, or 3 times/day
    pricelist_time1_hour: Mapped[int] = mapped_column(Integer, default=10)
    pricelist_time1_minute: Mapped[int] = mapped_column(Integer, default=0)
    pricelist_time2_hour: Mapped[int] = mapped_column(Integer, default=18)
    pricelist_time2_minute: Mapped[int] = mapped_column(Integer, default=0)
    pricelist_time3_hour: Mapped[int] = mapped_column(Integer, default=14)
    pricelist_time3_minute: Mapped[int] = mapped_column(Integer, default=0)


class ChannelPost(Base):
    __tablename__ = "channel_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    message_id: Mapped[int] = mapped_column(BigInteger)  # Telegram message_id
    channel_id: Mapped[int] = mapped_column(BigInteger)  # Telegram channel_id
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="channel_posts", lazy="selectin")
