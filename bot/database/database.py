from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Sequence
import os

from .models import (
    Base, User, Category, Brand, Product, Supply, SupplyItem,
    Sale, WriteOff, Reservation, ChannelPost, UserRole, ReservationStatus, WriteOffReason
)
from ..config import settings


class Database:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        # Ensure data directory exists for SQLite
        if "sqlite" in self.database_url:
            db_path = self.database_url.split("///")[-1]
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

        self.engine = create_async_engine(self.database_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        return self.session_factory()

    # ==================== USER METHODS ====================

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> User:
        """Get or create user by telegram_id"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                # Update user info if changed
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                if updated:
                    await session.commit()
                    await session.refresh(user)

            return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()

    async def set_user_role(self, telegram_id: int, role: UserRole) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.role = role
                await session.commit()
                await session.refresh(user)
            return user

    async def get_all_admins(self) -> Sequence[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.role.in_([UserRole.ADMIN, UserRole.OWNER]))
            )
            return result.scalars().all()

    async def set_user_phone(self, telegram_id: int, phone: str) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.phone = phone
                await session.commit()
                await session.refresh(user)
            return user

    # ==================== CATEGORY METHODS ====================

    async def create_category(self, name: str, description: str = None) -> Category:
        async with self.session_factory() as session:
            category = Category(name=name, description=description)
            session.add(category)
            await session.commit()
            await session.refresh(category)
            return category

    async def get_all_categories(self, active_only: bool = True) -> Sequence[Category]:
        async with self.session_factory() as session:
            query = select(Category).order_by(Category.sort_order, Category.name)
            if active_only:
                query = query.where(Category.is_active == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Category).where(Category.id == category_id)
            )
            return result.scalar_one_or_none()

    async def update_category(self, category_id: int, **kwargs) -> Optional[Category]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Category).where(Category.id == category_id)
            )
            category = result.scalar_one_or_none()
            if category:
                for key, value in kwargs.items():
                    if hasattr(category, key):
                        setattr(category, key, value)
                await session.commit()
                await session.refresh(category)
            return category

    async def delete_category(self, category_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Category).where(Category.id == category_id)
            )
            category = result.scalar_one_or_none()
            if category:
                category.is_active = False
                await session.commit()
                return True
            return False

    # ==================== BRAND METHODS ====================

    async def create_brand(self, category_id: int, name: str, description: str = None) -> Brand:
        async with self.session_factory() as session:
            brand = Brand(category_id=category_id, name=name, description=description)
            session.add(brand)
            await session.commit()
            await session.refresh(brand)
            return brand

    async def get_brands_by_category(self, category_id: int, active_only: bool = True) -> Sequence[Brand]:
        async with self.session_factory() as session:
            query = select(Brand).where(Brand.category_id == category_id).order_by(Brand.sort_order, Brand.name)
            if active_only:
                query = query.where(Brand.is_active == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_all_brands(self, active_only: bool = True) -> Sequence[Brand]:
        async with self.session_factory() as session:
            query = select(Brand).order_by(Brand.name)
            if active_only:
                query = query.where(Brand.is_active == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_brand_by_id(self, brand_id: int) -> Optional[Brand]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Brand).where(Brand.id == brand_id)
            )
            return result.scalar_one_or_none()

    async def update_brand(self, brand_id: int, **kwargs) -> Optional[Brand]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Brand).where(Brand.id == brand_id)
            )
            brand = result.scalar_one_or_none()
            if brand:
                for key, value in kwargs.items():
                    if hasattr(brand, key):
                        setattr(brand, key, value)
                await session.commit()
                await session.refresh(brand)
            return brand

    async def delete_brand(self, brand_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Brand).where(Brand.id == brand_id)
            )
            brand = result.scalar_one_or_none()
            if brand:
                brand.is_active = False
                await session.commit()
                return True
            return False

    # ==================== PRODUCT METHODS ====================

    async def create_product(
        self,
        brand_id: int,
        name: str,
        purchase_price: float = 0,
        sale_price: float = 0,
        quantity: int = 0,
        description: str = None,
        photo_file_id: str = None
    ) -> Product:
        async with self.session_factory() as session:
            product = Product(
                brand_id=brand_id,
                name=name,
                purchase_price=purchase_price,
                sale_price=sale_price,
                quantity=quantity,
                description=description,
                photo_file_id=photo_file_id
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    async def get_products_by_brand(self, brand_id: int, available_only: bool = False) -> Sequence[Product]:
        async with self.session_factory() as session:
            query = select(Product).where(
                Product.brand_id == brand_id,
                Product.is_available == True
            ).order_by(Product.name)
            if available_only:
                query = query.where(Product.quantity > 0)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_all_products(self, available_only: bool = False, in_stock_only: bool = False) -> Sequence[Product]:
        async with self.session_factory() as session:
            query = select(Product).where(Product.is_available == True).order_by(Product.name)
            if in_stock_only:
                query = query.where(Product.quantity > 0)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            return result.scalar_one_or_none()

    async def update_product(self, product_id: int, **kwargs) -> Optional[Product]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                for key, value in kwargs.items():
                    if hasattr(product, key):
                        setattr(product, key, value)
                await session.commit()
                await session.refresh(product)
            return product

    async def update_product_quantity(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """Update product quantity (positive to add, negative to subtract)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.quantity = max(0, product.quantity + quantity_change)
                await session.commit()
                await session.refresh(product)
            return product

    async def delete_product(self, product_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.is_available = False
                await session.commit()
                return True
            return False

    async def search_products(self, query: str) -> Sequence[Product]:
        """Search products by name"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(
                    Product.is_available == True,
                    Product.name.ilike(f"%{query}%")
                ).order_by(Product.name)
            )
            return result.scalars().all()

    async def get_low_stock_products(self, threshold: int = 3) -> Sequence[Product]:
        """Get products with quantity below threshold"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(
                    Product.is_available == True,
                    Product.quantity <= threshold,
                    Product.quantity > 0
                ).order_by(Product.quantity)
            )
            return result.scalars().all()

    # ==================== SUPPLY METHODS ====================

    async def create_supply(
        self,
        items: List[dict],
        supplier_name: str = None,
        notes: str = None,
        created_by_id: int = None
    ) -> Supply:
        """
        Create a supply with items.
        items: list of dicts with keys: product_id, quantity, purchase_price
        """
        async with self.session_factory() as session:
            total_amount = sum(item["quantity"] * item["purchase_price"] for item in items)

            supply = Supply(
                supplier_name=supplier_name,
                total_amount=total_amount,
                notes=notes,
                created_by_id=created_by_id
            )
            session.add(supply)
            await session.flush()

            for item_data in items:
                supply_item = SupplyItem(
                    supply_id=supply.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    purchase_price=item_data["purchase_price"]
                )
                session.add(supply_item)

                # Update product quantity and price
                result = await session.execute(
                    select(Product).where(Product.id == item_data["product_id"])
                )
                product = result.scalar_one_or_none()
                if product:
                    product.quantity += item_data["quantity"]
                    product.purchase_price = item_data["purchase_price"]

            await session.commit()
            await session.refresh(supply)
            return supply

    async def get_supply_by_id(self, supply_id: int) -> Optional[Supply]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Supply).where(Supply.id == supply_id)
            )
            return result.scalar_one_or_none()

    async def get_supplies(self, limit: int = 50) -> Sequence[Supply]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Supply).order_by(Supply.created_at.desc()).limit(limit)
            )
            return result.scalars().all()

    # ==================== SALE METHODS ====================

    async def create_sale(
        self,
        product_id: int,
        quantity: int = 1,
        sale_price: float = None,
        notes: str = None,
        sold_by_id: int = None
    ) -> Optional[Sale]:
        """Create a sale and update product quantity"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product or product.quantity < quantity:
                return None

            sale = Sale(
                product_id=product_id,
                quantity=quantity,
                sale_price=sale_price or product.sale_price,
                purchase_price=product.purchase_price,
                notes=notes,
                sold_by_id=sold_by_id
            )
            session.add(sale)

            # Update product quantity
            product.quantity -= quantity

            await session.commit()
            await session.refresh(sale)
            return sale

    async def get_sales_by_period(
        self,
        start_date: datetime,
        end_date: datetime = None
    ) -> Sequence[Sale]:
        async with self.session_factory() as session:
            query = select(Sale).where(Sale.sold_at >= start_date)
            if end_date:
                query = query.where(Sale.sold_at <= end_date)
            query = query.order_by(Sale.sold_at.desc())
            result = await session.execute(query)
            return result.scalars().all()

    async def get_today_sales(self) -> Sequence[Sale]:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.get_sales_by_period(today)

    async def get_sales_statistics(
        self,
        start_date: datetime,
        end_date: datetime = None
    ) -> dict:
        """Get sales statistics for a period"""
        async with self.session_factory() as session:
            query = select(Sale).where(Sale.sold_at >= start_date)
            if end_date:
                query = query.where(Sale.sold_at <= end_date)

            result = await session.execute(query)
            sales = result.scalars().all()

            total_revenue = sum(s.sale_price * s.quantity for s in sales)
            total_cost = sum(s.purchase_price * s.quantity for s in sales)
            total_profit = total_revenue - total_cost
            total_items = sum(s.quantity for s in sales)

            return {
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "total_items": total_items,
                "sales_count": len(sales)
            }

    # ==================== WRITE-OFF METHODS ====================

    async def create_write_off(
        self,
        product_id: int,
        quantity: int,
        reason: WriteOffReason,
        notes: str = None,
        created_by_id: int = None
    ) -> Optional[WriteOff]:
        """Create a write-off and update product quantity"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product or product.quantity < quantity:
                return None

            write_off = WriteOff(
                product_id=product_id,
                quantity=quantity,
                reason=reason,
                notes=notes,
                created_by_id=created_by_id
            )
            session.add(write_off)

            # Update product quantity
            product.quantity -= quantity

            await session.commit()
            await session.refresh(write_off)
            return write_off

    async def get_write_offs(self, limit: int = 50) -> Sequence[WriteOff]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WriteOff).order_by(WriteOff.created_at.desc()).limit(limit)
            )
            return result.scalars().all()

    # ==================== RESERVATION METHODS ====================

    async def create_reservation(
        self,
        product_id: int,
        user_id: int,
        quantity: int = 1,
        hours: int = 24,
        notes: str = None
    ) -> Optional[Reservation]:
        """Create a reservation"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product or product.quantity < quantity:
                return None

            expires_at = datetime.utcnow() + timedelta(hours=hours)

            reservation = Reservation(
                product_id=product_id,
                user_id=user_id,
                quantity=quantity,
                expires_at=expires_at,
                notes=notes
            )
            session.add(reservation)

            # Reserve product (decrease available quantity)
            product.quantity -= quantity

            await session.commit()
            await session.refresh(reservation)
            return reservation

    async def get_active_reservations(self) -> Sequence[Reservation]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reservation).where(
                    Reservation.status == ReservationStatus.ACTIVE
                ).order_by(Reservation.expires_at)
            )
            return result.scalars().all()

    async def get_user_reservations(self, user_id: int) -> Sequence[Reservation]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reservation).where(
                    Reservation.user_id == user_id,
                    Reservation.status == ReservationStatus.ACTIVE
                ).order_by(Reservation.expires_at)
            )
            return result.scalars().all()

    async def complete_reservation(self, reservation_id: int) -> Optional[Reservation]:
        """Complete reservation (product was sold)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reservation).where(Reservation.id == reservation_id)
            )
            reservation = result.scalar_one_or_none()

            if reservation and reservation.status == ReservationStatus.ACTIVE:
                reservation.status = ReservationStatus.COMPLETED
                await session.commit()
                await session.refresh(reservation)

            return reservation

    async def cancel_reservation(self, reservation_id: int) -> Optional[Reservation]:
        """Cancel reservation and return product to stock"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reservation).where(Reservation.id == reservation_id)
            )
            reservation = result.scalar_one_or_none()

            if reservation and reservation.status == ReservationStatus.ACTIVE:
                reservation.status = ReservationStatus.CANCELLED

                # Return product to stock
                result = await session.execute(
                    select(Product).where(Product.id == reservation.product_id)
                )
                product = result.scalar_one_or_none()
                if product:
                    product.quantity += reservation.quantity

                await session.commit()
                await session.refresh(reservation)

            return reservation

    async def expire_old_reservations(self) -> List[Reservation]:
        """Expire old reservations and return products to stock"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reservation).where(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.expires_at < datetime.utcnow()
                )
            )
            expired = result.scalars().all()

            for reservation in expired:
                reservation.status = ReservationStatus.EXPIRED

                # Return product to stock
                result = await session.execute(
                    select(Product).where(Product.id == reservation.product_id)
                )
                product = result.scalar_one_or_none()
                if product:
                    product.quantity += reservation.quantity

            await session.commit()
            return list(expired)

    async def get_expiring_reservations(self, hours: int = 2) -> Sequence[Reservation]:
        """Get reservations expiring within specified hours"""
        async with self.session_factory() as session:
            expires_before = datetime.utcnow() + timedelta(hours=hours)
            result = await session.execute(
                select(Reservation).where(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.expires_at <= expires_before,
                    Reservation.expires_at > datetime.utcnow()
                ).order_by(Reservation.expires_at)
            )
            return result.scalars().all()

    # ==================== CHANNEL POST METHODS ====================

    async def create_channel_post(
        self,
        product_id: int,
        message_id: int,
        channel_id: int
    ) -> ChannelPost:
        async with self.session_factory() as session:
            post = ChannelPost(
                product_id=product_id,
                message_id=message_id,
                channel_id=channel_id
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post

    async def get_channel_post_by_product(self, product_id: int) -> Optional[ChannelPost]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChannelPost).where(
                    ChannelPost.product_id == product_id,
                    ChannelPost.is_sold == False
                ).order_by(ChannelPost.created_at.desc())
            )
            return result.scalar_one_or_none()

    async def mark_channel_post_sold(self, post_id: int) -> Optional[ChannelPost]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChannelPost).where(ChannelPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if post:
                post.is_sold = True
                await session.commit()
                await session.refresh(post)
            return post


# Global database instance
_db: Optional[Database] = None


async def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        await _db.init_db()
    return _db
