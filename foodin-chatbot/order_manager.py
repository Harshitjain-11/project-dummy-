"""
PRODUCTION OrderManager - 100% DINEaus Compatible
Database: college_practice
Fully aligned with your actual production schema
"""

import mysql.connector
from mysql.connector import errorcode
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

class OrderManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self._conn = None
        self._connect()

    def _connect(self):
        try:
            self._conn = mysql.connector.connect(**self.db_config)
            print("✅ MySQL connection established")
        except mysql.connector.Error as err:
            print(f"❌ MySQL connection error: {err}")
            raise

    def close(self):
        if self._conn:
            self._conn.close()

    # ===============================
    # RESTAURANT & MENU METHODS
    # ===============================
    
    def get_restaurants(self) -> List[Dict[str, Any]]:
        """Get all approved restaurants"""
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, location FROM restaurant WHERE status = 'approved' ORDER BY id"
            )
            rows = cursor.fetchall()
            return rows if rows else []
        except Exception as e:
            print(f"Error fetching restaurants: {e}")
            return []
        finally:
            cursor.close()
    
    def get_menu(self, restaurant_id: int) -> List[Dict[str, Any]]:
        """Get available menu items for a restaurant"""
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT item_name, price FROM menu_item "
                "WHERE restaurant_id = %s AND is_available = TRUE",
                (restaurant_id,)
            )
            rows = cursor.fetchall()
            return rows if rows else []
        except Exception as e:
            print(f"Error fetching menu for restaurant {restaurant_id}: {e}")
            return []
        finally:
            cursor.close()

    # ===============================
    # ORDER METHODS - PRODUCTION SCHEMA
    # ===============================
    
    def add_order(self, user_id: int, restaurant_id: int, items: List[Dict[str, Any]], total_price: float, address_id: int = None) -> int:
        """
        Create new order in production orders table
        
        Schema: orders
        - id INT AUTO_INCREMENT PRIMARY KEY
        - user_id INT NOT NULL
        - restaurant_id INT NOT NULL
        - items JSON NOT NULL
        - total_price DECIMAL(10,2) NOT NULL
        - address_id INT (optional)
        - status ENUM('scheduled','pending','accepted','preparing','ready',
                      'out_for_delivery','picked_up','delivered','completed',
                      'rejected','cancelled') DEFAULT 'pending'
        - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
        items_json = json.dumps(items, default=str)
        
        # Default user_id if not provided
        if not user_id or user_id == "anonymous":
            user_id = 1

        cursor = self._conn.cursor()
        try:
            print(f"📝 Creating Order:")
            print(f"   User: {user_id}")
            print(f"   Restaurant: {restaurant_id}")
            print(f"   Items: {len(items)} items")
            print(f"   Total: ₹{total_price}")
            
            cursor.execute(
                """
                INSERT INTO orders 
                (user_id, restaurant_id, items, total_price, address_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'pending', NOW())
                """,
                (user_id, restaurant_id, items_json, total_price, address_id)
            )
            self._conn.commit()
            
            order_id = cursor.lastrowid
            print(f"✅ Order #{order_id} created successfully!")
            return order_id
            
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error creating order: {e}")
            raise
        finally:
            cursor.close()

    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve order by INT id"""
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Parse JSON items
            if row.get('items'):
                try:
                    row['items'] = json.loads(row['items'])
                except:
                    row['items'] = []
            
            # Add aliases for backward compatibility
            row['order_id'] = row['id']
            row['total'] = row.get('total_price', 0)
            
            return row
        finally:
            cursor.close()

    def confirm_order(self, order_id: int) -> bool:
        """
        Confirm order - change status from 'pending' to 'accepted'
        Also updates accepted_at timestamp if column exists
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            row = cursor.fetchone()
            if not row:
                print(f"⚠️ Order {order_id} not found")
                return False
            
            current_status = row[0]
            
            if current_status == "pending":
                # Try to update accepted_at if column exists
                try:
                    cursor.execute(
                        "UPDATE orders SET status = 'accepted', accepted_at = NOW() WHERE id = %s",
                        (order_id,)
                    )
                except:
                    # Fallback if accepted_at column doesn't exist
                    cursor.execute(
                        "UPDATE orders SET status = 'accepted' WHERE id = %s",
                        (order_id,)
                    )
                
                self._conn.commit()
                print(f"✅ Order #{order_id} confirmed (status: accepted)")
                return True
            
            print(f"ℹ️ Order #{order_id} already in status: {current_status}")
            return True
            
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error confirming order: {e}")
            raise
        finally:
            cursor.close()

    def cancel_order(self, order_id: int, reason: Optional[str] = None) -> bool:
        """
        Cancel order - change status to 'cancelled'
        Cannot cancel if already: delivered, completed
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE orders 
                SET status = 'cancelled' 
                WHERE id = %s 
                AND status NOT IN ('delivered', 'completed')
                """,
                (order_id,)
            )
            
            if cursor.rowcount == 0:
                print(f"⚠️ Cannot cancel order #{order_id} (already delivered/completed)")
                return False
            
            self._conn.commit()
            print(f"✅ Order #{order_id} cancelled")
            return True
            
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error cancelling order: {e}")
            raise
        finally:
            cursor.close()

    def track_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Track order status by INT id"""
        return self.get_order(order_id)

    def update_order_status(self, order_id: int, new_status: str, update_timestamp: bool = True) -> bool:
        """
        Update order status to valid ENUM value
        
        Valid statuses:
        - scheduled, pending, accepted, preparing, ready
        - out_for_delivery, picked_up, delivered
        - completed, rejected, cancelled
        """
        valid_statuses = [
            "scheduled", "pending", "accepted", "preparing", "ready",
            "out_for_delivery", "picked_up", "delivered",
            "completed", "rejected", "cancelled"
        ]
        
        if new_status not in valid_statuses:
            print(f"❌ Invalid status: {new_status}")
            return False
        
        cursor = self._conn.cursor()
        try:
            # Map status to timestamp column
            timestamp_map = {
                'accepted': 'accepted_at',
                'preparing': 'preparing_at',
                'ready': 'ready_at',
                'picked_up': 'picked_up_at',
                'out_for_delivery': 'out_for_delivery_at',
                'delivered': 'delivered_at'
            }
            
            timestamp_col = timestamp_map.get(new_status)
            
            if timestamp_col and update_timestamp:
                try:
                    cursor.execute(
                        f"UPDATE orders SET status = %s, {timestamp_col} = NOW() WHERE id = %s",
                        (new_status, order_id)
                    )
                except:
                    # Fallback if timestamp column doesn't exist
                    cursor.execute(
                        "UPDATE orders SET status = %s WHERE id = %s",
                        (new_status, order_id)
                    )
            else:
                cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s",
                    (new_status, order_id)
                )
            
            self._conn.commit()
            print(f"✅ Order #{order_id} status → {new_status}")
            return cursor.rowcount > 0
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error updating status: {e}")
            raise
        finally:
            cursor.close()

    # ===============================
    # RESERVATION METHODS - PRODUCTION SCHEMA
    # ===============================
    
    def book_table(self, user_id: int, restaurant_id: int, customer_name: str, 
                   customer_phone: str, booking_date: str, time_slot: str, 
                   guests: int) -> int:
        """
        Create table reservation in PRODUCTION reservations table
        
        Schema: reservations
        - id INT AUTO_INCREMENT PRIMARY KEY
        - restaurant_id INT NOT NULL
        - customer_name VARCHAR(255) NOT NULL
        - customer_phone VARCHAR(30) NOT NULL
        - date DATE NOT NULL
        - time_slot VARCHAR(20) NOT NULL
        - guests INT NOT NULL
        - user_id INT
        - status ENUM('pending','accepted','arrived','completed','rejected','cancelled')
        - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
        cursor = self._conn.cursor()
        try:
            # Default user_id if anonymous
            if not user_id or user_id == "anonymous":
                user_id = 1
            
            print(f"📅 Creating Reservation:")
            print(f"   Restaurant: {restaurant_id}")
            print(f"   Customer: {customer_name}")
            print(f"   Date: {booking_date}")
            print(f"   Time: {time_slot}")
            print(f"   Guests: {guests}")
            
            cursor.execute(
                """
                INSERT INTO reservations 
                (restaurant_id, customer_name, customer_phone, date, time_slot, 
                 guests, user_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                """,
                (restaurant_id, customer_name, customer_phone, booking_date, 
                 time_slot, guests, user_id)
            )
            self._conn.commit()
            
            booking_id = cursor.lastrowid
            print(f"✅ Reservation #{booking_id} created successfully!")
            return booking_id
            
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error creating reservation: {e}")
            raise
        finally:
            cursor.close()

    def get_reservation(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve reservation by ID"""
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def cancel_reservation(self, reservation_id: int) -> bool:
        """Cancel reservation - change status to 'cancelled'"""
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE reservations 
                SET status = 'cancelled' 
                WHERE id = %s 
                AND status NOT IN ('completed', 'cancelled')
                """,
                (reservation_id,)
            )
            self._conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Reservation #{reservation_id} cancelled")
                return True
            else:
                print(f"⚠️ Cannot cancel reservation #{reservation_id}")
                return False
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error cancelling reservation: {e}")
            raise
        finally:
            cursor.close()

    def update_reservation_status(self, reservation_id: int, new_status: str) -> bool:
        """
        Update reservation status
        Valid: pending, accepted, arrived, completed, rejected, cancelled
        """
        valid_statuses = ['pending', 'accepted', 'arrived', 'completed', 'rejected', 'cancelled']
        
        if new_status not in valid_statuses:
            print(f"❌ Invalid reservation status: {new_status}")
            return False
        
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "UPDATE reservations SET status = %s WHERE id = %s",
                (new_status, reservation_id)
            )
            self._conn.commit()
            print(f"✅ Reservation #{reservation_id} status → {new_status}")
            return cursor.rowcount > 0
        except Exception as e:
            self._conn.rollback()
            print(f"❌ Error updating reservation status: {e}")
            raise
        finally:
            cursor.close()
