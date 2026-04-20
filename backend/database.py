#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型和操作
使用MySQL数据库
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import json
import pymysql

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '15066577233',
    'database': 'smartpark',
    'charset': 'utf8mb4'
}


# 创建数据库连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 数据库基类
Base = declarative_base()

# ============== 数据库模型 ==============

class User(Base):
    """用户表（Web版）"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="登录用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), nullable=True, comment="用户昵称")
    avatar_url = Column(String(255), nullable=True, comment="用户头像URL")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")


class UserVehicle(Base):
    """用户车辆绑定表"""
    __tablename__ = "user_vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="关联的用户ID")
    plate_number = Column(String(20), nullable=False, index=True, comment="车牌号")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否为默认车辆")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="绑定时间")



class ParkingSpot(Base):
    """车位表"""
    __tablename__ = "parking_spots"
    
    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(String(10), unique=True, nullable=False, comment="车位编号")
    occupied = Column(Boolean, default=False, nullable=False, comment="是否被占用")
    entry_time = Column(DateTime, nullable=True, comment="进入时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")


class ParkingRecord(Base):
    """停车记录表"""
    __tablename__ = "parking_records"
    
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(50), unique=True, nullable=False, comment="记录ID")
    plate_number = Column(String(20), nullable=False, index=True, comment="车牌号")
    spot_id = Column(String(10), nullable=False, comment="车位编号")
    entry_time = Column(DateTime, nullable=False, comment="入场时间")
    exit_time = Column(DateTime, nullable=True, comment="出场时间")
    duration = Column(String(50), nullable=True, comment="停车时长")
    amount = Column(Float, default=0.0, nullable=False, comment="应付金额")
    paid = Column(Boolean, default=False, nullable=False, comment="是否已支付")
    paid_time = Column(DateTime, nullable=True, comment="支付时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")


class BillingRecord(Base):
    """计费记录表"""
    __tablename__ = "billing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False, comment="订单ID")
    record_id = Column(String(50), nullable=True, comment="关联的停车记录ID")
    plate_number = Column(String(20), nullable=False, index=True, comment="车牌号")
    amount = Column(Float, nullable=False, comment="支付金额")
    payment_method = Column(String(20), nullable=True, comment="支付方式")
    paid = Column(Boolean, default=True, nullable=False, comment="是否已支付")
    paid_time = Column(DateTime, default=datetime.now, nullable=False, comment="支付时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")


# ============== 数据库操作类 ==============

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=engine)
    
    def get_parking_spot(self, spot_id: str) -> ParkingSpot:
        """获取车位信息"""
        return self.session.query(ParkingSpot).filter(ParkingSpot.spot_id == spot_id).first()
    
    def get_all_parking_spots(self) -> list:
        """获取所有车位信息"""
        return self.session.query(ParkingSpot).all()
    
    def update_parking_spot(self, spot_id: str, occupied: bool) -> bool:
        """更新车位状态（统一版）"""
        spot = self.get_parking_spot(spot_id)
        if not spot:
            return False
        
        spot.occupied = occupied
        spot.updated_at = datetime.now()
        
        if occupied:
            spot.entry_time = datetime.now()
        else:
            spot.entry_time = None
        
        self.session.commit()
        return True
    
    def create_parking_record(self, plate_number: str, spot_id: str) -> ParkingRecord:
        """创建停车记录"""
        record = ParkingRecord(
            record_id=f"record_{int(datetime.now().timestamp())}",
            plate_number=plate_number,
            spot_id=spot_id,
            entry_time=datetime.now(),
            paid=False
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record
    
    def update_parking_record_exit(self, plate_number: str, exit_time: datetime = None) -> bool:
        """更新停车记录出场时间"""
        record = self.session.query(ParkingRecord).filter(
            ParkingRecord.plate_number == plate_number,
            ParkingRecord.exit_time == None
        ).first()
        
        if not record:
            return False
        
        if exit_time is None:
            exit_time = datetime.now()
        
        record.exit_time = exit_time
        record.updated_at = datetime.now()
        
        # 计算停车时长
        duration = (exit_time - record.entry_time).total_seconds()
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        
        if hours > 0:
            record.duration = f"{hours}小时{minutes}分钟"
        else:
            record.duration = f"{minutes}分钟"
        
        # 计算停车费用
        record.amount = self.calculate_fee(record.entry_time, exit_time)
        
        self.session.commit()
        return True
    
    def calculate_fee(self, entry_time: datetime, exit_time: datetime) -> float:
        """计算停车费用"""
        duration = (exit_time - entry_time).total_seconds() / 3600  # 小时
        
        # 计费规则
        if duration <= 1:
            fee = 5.0
        else:
            fee = 5.0 + ((duration - 1) * 6.0)  # 超过1小时，每小时6元
        
        # 每日封顶50元
        fee = min(fee, 50.0)
        
        return round(fee, 2)
    
    def get_billing_info(self, plate_number: str) -> dict:
        """获取计费信息"""
        # 查找未支付的记录
        record = self.session.query(ParkingRecord).filter(
            ParkingRecord.plate_number == plate_number,
            ParkingRecord.exit_time != None
        ).first()
        
        if not record:
            # 查找已出场的记录
            record = self.session.query(ParkingRecord).filter(
                ParkingRecord.plate_number == plate_number
            ).order_by(ParkingRecord.created_at.desc()).first()
        
        if not record:
            return None
        
        return {
            'plateNumber': record.plate_number,
            'entryTime': record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exitTime': record.exit_time.strftime('%Y-%m-%d %H:%M:%S') if record.exit_time else None,
            'duration': record.duration,
            'spot': record.spot_id,
            'amount': record.amount,
            'paid': record.paid
        }
    
    def get_unpaid_record(self, plate_number: str) -> dict:
        """获取未支付记录"""
        record = self.session.query(ParkingRecord).filter(
            ParkingRecord.plate_number == plate_number,
            ParkingRecord.exit_time != None,
            ParkingRecord.paid == False
        ).first()
        
        if not record:
            return None
        
        return {
            'plateNumber': record.plate_number,
            'entryTime': record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exitTime': record.exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': record.duration,
            'spotId': record.spot_id,
            'amount': record.amount,
            'paid': record.paid
        }
    
    def pay_bill(self, plate_number: str, amount: float, payment_method: str = "wechat") -> bool:
        """支付账单"""
        record = self.session.query(ParkingRecord).filter(
            ParkingRecord.plate_number == plate_number,
            ParkingRecord.exit_time != None,
            ParkingRecord.paid == False
        ).first()
        
        if not record:
            return False
        
        record.paid = True
        record.paid_time = datetime.now()
        
        # 创建计费记录
        billing = BillingRecord(
            order_id=f"order_{int(datetime.now().timestamp())}",
            record_id=record.record_id,
            plate_number= plate_number,
            amount=amount,
            payment_method=payment_method,
            paid=True
        )
        self.session.add(billing)
        self.session.commit()
        
        return True
    
    def get_billing_history(self, plate_number: str = None, page: int = 1, page_size: int = 10) -> dict:
        """获取计费历史"""
        query = self.session.query(ParkingRecord)
        
        if plate_number:
            query = query.filter(ParkingRecord.plate_number == plate_number)
        
        total = query.count()
        
        # 分页
        records = query.order_by(ParkingRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            'total': total,
            'page': page,
            'pageSize': page_size,
            'records': [
                {
                    'id': record.record_id,
                    'plateNumber': record.plate_number,
                    'entryTime': record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'exitTime': record.exit_time.strftime('%Y-%m-%d %H:%M:%S') if record.exit_time else None,
                    'duration': record.duration,
                    'spot': record.spot_id,
                    'amount': record.amount,
                    'paid': record.paid,
                    'paidTime': record.paid_time.strftime('%Y-%m-%d %H:%M:%S') if record.paid_time else None
                }
                for record in records
            ]
        }
    
    def update_spot_status(self, spot_id: str, occupied: bool) -> bool:
        """更新车位状态（传感器接口调用）- update_parking_spot 的别名"""
        return self.update_parking_spot(spot_id, occupied)

    def get_parking_status(self) -> dict:
        """获取停车场状态"""
        spots = self.get_all_parking_spots()
        total_spots = len(spots)
        occupied_spots = sum(1 for spot in spots if spot.occupied)
        available_spots = total_spots - occupied_spots
        
        return {
            'totalSpots': total_spots,
            'availableSpots': available_spots,
            'occupiedSpots': occupied_spots,
            'spots': [
                {
                    'id': spot.spot_id,
                    'occupied': spot.occupied,
                    'entryTime': spot.entry_time.strftime('%Y-%m-%d %H:%M:%S') if spot.entry_time else None
                }
                for spot in spots
            ]
        }
        
    def update_user_profile(self, user_id: int, nickname: str = None, avatar_url: str = None) -> bool:
        """更新用户信息"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        if nickname is not None:
            user.nickname = nickname
        if avatar_url is not None:
            user.avatar_url = avatar_url
            
        user.updated_at = datetime.now()
        self.session.commit()
        return True
        
    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """更新用户密码"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        user.password_hash = new_password_hash
        user.updated_at = datetime.now()
        self.session.commit()
        return True
        
    def delete_user(self, user_id: int) -> bool:
        """注销用户"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        # Optional: delete related records like UserVehicle
        self.session.query(UserVehicle).filter(UserVehicle.user_id == user_id).delete()
        
        self.session.delete(user)
        self.session.commit()
        return True


# 初始化数据库
def init_database():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化车位数据
    db = DatabaseManager()
    with db as session:
        # 检查是否已有车位数据
        existing_spots = session.query(ParkingSpot).all()
        if not existing_spots:
            # 创建初始车位
            spots_data = [
                ParkingSpot(spot_id='A', occupied=False),
                ParkingSpot(spot_id='B', occupied=False)
            ]
            session.add_all(spots_data)
            session.commit()
            print("初始化车位数据：A、B")


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成")
