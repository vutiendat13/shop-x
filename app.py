from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
import sqlite3, hashlib, json, os, secrets, time, math
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
DB_PATH = 'shopee.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            security_question TEXT,
            security_answer TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '🛍️'
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            sale_price REAL,
            sale_end TEXT,
            stock INTEGER DEFAULT 0,
            category_id INTEGER,
            image TEXT,
            video TEXT,
            sold INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total REAL,
            status TEXT DEFAULT 'pending',
            address TEXT,
            phone TEXT,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS flash_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            discount_percent INTEGER,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            type TEXT DEFAULT 'banner',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    seed_data(conn)
    conn.close()

def seed_data(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] > 0:
        return

    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, ?)",
              ('admin@shopx.vn', hash_password('admin123'), 'Admin', 1))
    c.execute("INSERT INTO users (email, password, name, security_question, security_answer) VALUES (?, ?, ?, ?, ?)",
              ('demo@shopx.vn', hash_password('demo123'), 'Demo User', 'Tên thú cưng?', hash_password('miu')))

    categories = [
        ('Thời trang', '👗'), ('Mỹ phẩm', '💄'), ('Điện tử', '📱'),
        ('Phụ kiện điện thoại', '🔌'), ('Đồ gia dụng', '🏠'), ('Thực phẩm', '🍎'),
        ('Đồ chơi', '🧸'), ('Mẹ & Bé', '👶'), ('Thú cưng', '🐾'),
        ('Thể thao', '⚽'), ('Xe cộ', '🚗'), ('Sách', '📚'),
        ('Văn phòng phẩm', '✏️'), ('Đồ decor', '🎨'), ('Thiết bị công nghệ', '💻'),
        ('Hàng handmade', '🧶'), ('Hàng tiêu dùng', '🛒')
    ]
    for name, icon in categories:
        c.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon))

    products = [
        ('Áo thun basic nam', 'Áo thun cotton 100% thoáng mát', 150000, 99000, 1, 50, 120),
        ('Quần jean skinny nữ', 'Quần jean co giãn 4 chiều', 320000, 220000, 1, 30, 85),
        ('Đầm maxi hoa nhí', 'Chất liệu lụa mềm mại', 280000, None, 1, 25, 42),
        ('Áo khoác bomber', 'Phong cách Hàn Quốc', 450000, 350000, 1, 20, 67),
        ('Set đồ thể thao nữ', 'Áo + quần legging cao cấp', 380000, 280000, 1, 15, 93),
        ('Son môi lì Romand', 'Màu sắc đa dạng, lâu trôi', 180000, 140000, 2, 100, 234),
        ('Kem chống nắng Anessa', 'SPF 50+, chống nước', 350000, None, 2, 80, 178),
        ('Serum vitamin C', 'Làm sáng da, giảm thâm nám', 220000, 180000, 2, 60, 145),
        ('Mặt nạ dưỡng ẩm', 'Hộp 10 miếng', 120000, 90000, 2, 200, 312),
        ('Tẩy trang Bioderma', 'Dịu nhẹ cho da nhạy cảm', 290000, 240000, 2, 70, 189),
        ('iPhone 15 Pro Max', 'Chip A17, camera 48MP', 34990000, 32990000, 3, 10, 23),
        ('Samsung Galaxy S24', 'AI camera, màn AMOLED', 22990000, 19990000, 3, 15, 41),
        ('Tai nghe Sony WH-1000XM5', 'Chống ồn ANC, 30h pin', 8990000, 7490000, 3, 20, 56),
        ('Apple Watch Series 9', 'Màn luôn sáng, GPS', 10990000, 9490000, 3, 8, 18),
        ('Loa JBL Flip 6', 'Chống nước IP67, âm thanh mạnh', 2990000, 2490000, 3, 25, 78),
        ('Ốp lưng iPhone 15', 'Chống sốc trong suốt', 85000, 60000, 4, 200, 445),
        ('Cáp sạc Type-C 1m', 'Sạc nhanh 65W', 120000, 85000, 4, 150, 387),
        ('Kính cường lực Samsung', 'Độ cứng 9H, chống vân tay', 95000, 65000, 4, 180, 523),
        ('Giá đỡ điện thoại xe', 'Xoay 360 độ, nam châm', 145000, 99000, 4, 100, 267),
        ('Sạc dự phòng Xiaomi 20000mAh', 'Sạc nhanh 2 cổng', 650000, 520000, 4, 50, 134),
        ('Nồi cơm điện Sharp', 'Dung tích 1.8L, không dính', 890000, 720000, 5, 20, 34),
        ('Máy xay sinh tố Philips', '600W, 1.5L', 1290000, 990000, 5, 15, 28),
        ('Bộ dao nhà bếp 6 món', 'Thép không gỉ cao cấp', 480000, 380000, 5, 30, 56),
        ('Nồi chiên không dầu', '5.5L kỹ thuật số', 1850000, 1490000, 5, 12, 21),
        ('Ấm đun siêu tốc Supor', '1.7L, 2200W', 420000, 320000, 5, 25, 47),
        ('Sữa tươi TH True Milk 1L', 'Không đường, thanh trùng', 38000, None, 6, 500, 892),
        ('Bánh quy socola Oreo', 'Gói 432g', 65000, 52000, 6, 300, 567),
        ('Dầu ăn Neptune 2L', 'Không cholesterol', 95000, 82000, 6, 200, 423),
        ('Mì tôm Hảo Hảo thùng 30 gói', 'Vị tôm chua cay', 180000, 155000, 6, 100, 312),
        ('Nước mắm Chin-su 1L', 'Độ đạm 40N', 65000, 55000, 6, 250, 489),
        ('Lego City cảnh sát', 'Bộ 500 mảnh ghép', 650000, 520000, 7, 30, 67),
        ('Búp bê Barbie Dreamhouse', 'Có nhà + phụ kiện', 890000, 720000, 7, 20, 43),
        ('Xe điều khiển từ xa', 'Tốc độ cao, chống va đập', 480000, 380000, 7, 25, 58),
        ('Bộ xếp hình gỗ 200 mảnh', 'An toàn cho bé từ 3 tuổi', 320000, 250000, 7, 40, 89),
        ('Robot thông minh lập trình', 'STEM giáo dục, pin sạc', 1290000, 990000, 7, 15, 31),
        ('Sữa công thức Nan 2', 'Cho bé 6-12 tháng, hộp 900g', 590000, 520000, 8, 50, 123),
        ('Xe đẩy em bé Joie', 'Gấp gọn, nhẹ 6kg', 3200000, 2800000, 8, 10, 18),
        ('Tã Pampers size M 76 miếng', 'Siêu mỏng, thấm hút', 280000, 240000, 8, 80, 234),
        ('Bình sữa Pigeon 200ml', 'Núm ti mềm tự nhiên', 185000, 150000, 8, 60, 178),
        ('Ghế ngồi ăn bé Stokke', 'Điều chỉnh độ cao', 4500000, 3990000, 8, 8, 12),
        ('Thức ăn hạt cho chó Royal Canin', 'Cho chó trưởng thành 4kg', 650000, 580000, 9, 40, 89),
        ('Cát vệ sinh mèo Bioline', 'Khử mùi nhanh, 10L', 185000, 150000, 9, 60, 145),
        ('Lồng chim cảnh', 'Inox cao cấp, dễ vệ sinh', 380000, 320000, 9, 20, 34),
        ('Đồ chơi cho mèo cần câu', 'Lông vũ đa màu', 85000, 65000, 9, 100, 267),
        ('Áo len cho chó', 'Ấm mùa đông, size S-XL', 145000, 110000, 9, 50, 123),
        ('Giày thể thao Nike Air Max', 'Đệm khí êm ái', 2890000, 2490000, 10, 20, 45),
        ('Bóng đá FIFA 5', 'Chính hãng, dùng thi đấu', 650000, 520000, 10, 30, 67),
        ('Gậy cầu lông Yonex', 'Cán carbon nhẹ', 890000, 720000, 10, 25, 48),
        ('Bình nước thể thao 1L', 'Inox 304, giữ lạnh 24h', 320000, 250000, 10, 60, 134),
        ('Thảm yoga cao su thiên nhiên', '6mm chống trượt', 580000, 450000, 10, 40, 89),
        ('Lốp xe máy Michelin', 'Size 70/90-17', 680000, 580000, 11, 30, 56),
        ('Dầu nhớt Castrol 10W-40', 'Hộp 4L', 580000, 480000, 11, 50, 89),
        ('Gương chiếu hậu xe máy', 'Chống rung, xoay 360', 145000, 110000, 11, 80, 178),
        ('Mũ bảo hiểm LS2 FF353', 'Fullface, tem QCVN', 1890000, 1590000, 11, 15, 23),
        ('Xăng dầu đốt máy nổ', 'Can nhựa 20L', 95000, None, 11, 40, 67),
        ('Đắc Nhân Tâm - Dale Carnegie', 'Bản dịch tiếng Việt', 85000, 68000, 12, 200, 456),
        ('Nhà Giả Kim - Paulo Coelho', 'Triết lý sống sâu sắc', 79000, 63000, 12, 180, 389),
        ('Python cho người mới bắt đầu', 'Lập trình từ cơ bản', 185000, 148000, 12, 100, 234),
        ('Harry Potter tập 1', 'Bản tiếng Việt mới nhất', 95000, 78000, 12, 150, 312),
        ('Học Tiếng Nhật N5', 'Có CD, bài tập', 145000, 115000, 12, 80, 178),
        ('Bút bi Thiên Long TL-023', 'Hộp 20 cái', 48000, 38000, 13, 500, 892),
        ('Tập học sinh 200 trang', 'Lốc 10 cuốn', 65000, 52000, 13, 300, 567),
        ('File kẹp tài liệu A4', 'Bộ 10 cái màu', 95000, 75000, 13, 200, 423),
        ('Máy tính casio fx-580VN', 'Khoa học, 549 hàm', 320000, 270000, 13, 50, 112),
        ('Kéo văn phòng inox', 'Bén, không gỉ', 35000, 28000, 13, 400, 678),
        ('Đèn ngủ LED cảm ứng', 'RGB 16 màu, điều khiển xa', 280000, 220000, 14, 60, 134),
        ('Tranh canvas phong cảnh', '60x90cm, khung gỗ', 450000, 350000, 14, 25, 48),
        ('Gương trang điểm LED', 'Đường kính 50cm, độ sáng điều chỉnh', 680000, 540000, 14, 20, 37),
        ('Vase gốm Bát Tràng', 'Họa tiết hoa sen', 320000, 250000, 14, 35, 67),
        ('Rèm cửa chống nắng', '2m x 1.5m, cách nhiệt', 580000, 450000, 14, 30, 54),
        ('Laptop Dell Inspiron 15', 'Core i5, 16GB RAM, 512 SSD', 18990000, 16990000, 15, 10, 18),
        ('Màn hình LG 24" IPS', '144Hz, FreeSync', 6490000, 5490000, 15, 15, 27),
        ('Bàn phím cơ Keychron K2', 'Blue switch, có đèn RGB', 2890000, 2490000, 15, 20, 43),
        ('Chuột gaming Logitech G102', '8000 DPI, 6 nút', 680000, 550000, 15, 30, 67),
        ('Webcam Logitech C920 HD', '1080p 30fps', 1890000, 1590000, 15, 15, 28),
        ('Túi vải thêu tay handmade', 'Họa tiết dân tộc độc đáo', 280000, None, 16, 20, 34),
        ('Nhẫn bạc khắc tên', 'Bạc 925, cá nhân hóa', 450000, 380000, 16, 30, 56),
        ('Tranh thêu chữ thập kit', 'Bộ đầy đủ, 40x50cm', 320000, 260000, 16, 25, 48),
        ('Nến thơm handmade', 'Sáp đậu nành, 200g', 185000, 150000, 16, 50, 112),
        ('Móc chìa khóa da bò', 'Khắc laser tên theo yêu cầu', 145000, None, 16, 40, 89),
        ('Nước rửa chén Sunlight 1kg', 'Hương chanh, diệt khuẩn', 48000, 38000, 17, 500, 892),
        ('Dung dịch vệ sinh nhà tắm', 'Tẩy sạch 99.9% vi khuẩn', 65000, 52000, 17, 300, 567),
        ('Kem đánh răng Colgate 230g', 'Than hoạt tính trắng răng', 52000, 42000, 17, 400, 734),
        ('Dầu gội Dove 640ml', 'Phục hồi tóc hư tổn', 145000, 115000, 17, 200, 423),
        ('Nước xả vải Comfort 1.6L', 'Hương hoa hồng', 125000, 99000, 17, 250, 489),
    ]

    product_images = [
        'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1586495777744-4e6232bf4ede?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1570194065650-d99fb4bedf0a?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1590156206657-aec5e5f2e6df?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1434493651957-4ec10c8e5e52?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1559447088-0c48c9d5d69c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1585515320310-259814833e62?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1626806819282-2c1dc01a5e0c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1526318896980-cf78c088247c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1612257999756-65ca5f9b4e40?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1535378620166-273708d44e4c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1519689680058-324335c77eba?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1609709295948-17d77cb2a69b?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1586495777744-4e6232bf4ede?w=400&h=400&fit=crop&sat=-50',
        'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1548802673-380ab8ebc7b7?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1560807707-8cc77767d783?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1544298621-35a764d40086?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1523362628745-0c100150b504?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop&hue=200',
        'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400&h=400&fit=crop&sat=-30',
        'https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1513001900722-370f803f498d?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1474932430478-367dbb6832c1?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1585952374809-3fcfe9e97c43?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1603217040830-dd96cf85754d?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1560472355-536de3962603?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1540932239986-30128078f3c5?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1580870069867-74c57ee1bb07?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1601370552761-d129028bd833?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1608181831718-c9d34e0e5245?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1589782182703-2aaa69037b5b?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1607613009820-a29f7bb81c04?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1585232350549-1b3c8f29f0dc?w=400&h=400&fit=crop',
        'https://images.unsplash.com/photo-1598452963314-b09f397a5c48?w=400&h=400&fit=crop',
    ]

    for i, (name, desc, price, sale_price, cat_id, stock, sold) in enumerate(products):
        img = product_images[i] if i < len(product_images) else f'https://images.unsplash.com/photo-{1500000000+i*12345}?w=400&h=400&fit=crop'
        c.execute("""INSERT INTO products (name, description, price, sale_price, category_id, stock, sold, image)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (name, desc, price, sale_price, cat_id, stock, sold, img))

    now = datetime.now()
    flash_end = (now + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
    for pid in [1, 6, 11, 31, 46, 56, 66]:
        c.execute("INSERT INTO flash_sales (product_id, discount_percent, start_time, end_time) VALUES (?, ?, ?, ?)",
                  (pid, 30, now.strftime('%Y-%m-%d %H:%M:%S'), flash_end))

    c.execute("INSERT INTO notifications (title, message, type, active) VALUES (?, ?, ?, 1)",
              ('🎉 Siêu sale hôm nay!', 'Giảm đến 50% hàng ngàn sản phẩm. Mua ngay!', 'popup'))
    c.execute("INSERT INTO notifications (title, message, type, active) VALUES (?, ?, ?, 1)",
              ('🚚 Miễn phí vận chuyển', 'Đơn hàng từ 150.000đ được miễn phí ship toàn quốc', 'banner'))

    conn.commit()

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    flash_sales = c.execute("""
        SELECT fs.*, p.name, p.image, p.price, p.sale_price, fs.end_time
        FROM flash_sales fs JOIN products p ON fs.product_id = p.id
        WHERE fs.end_time > ? AND fs.start_time <= ?
        LIMIT 8
    """, (now, now)).fetchall()
    categories = c.execute("SELECT * FROM categories").fetchall()
    sale_products = c.execute("""
        SELECT * FROM products WHERE sale_price IS NOT NULL ORDER BY (price - sale_price) DESC LIMIT 12
    """).fetchall()
    hot_products = c.execute("SELECT * FROM products ORDER BY sold DESC LIMIT 12").fetchall()
    new_products = c.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT 12").fetchall()
    notification = c.execute("SELECT * FROM notifications WHERE active=1 AND type='popup' LIMIT 1").fetchone()
    banner = c.execute("SELECT * FROM notifications WHERE active=1 AND type='banner' LIMIT 1").fetchone()
    conn.close()
    wishlist_ids = []
    if 'user_id' in session:
        conn2 = get_db()
        wishlist_ids = [r['product_id'] for r in conn2.execute("SELECT product_id FROM wishlist WHERE user_id=?", (session['user_id'],)).fetchall()]
        conn2.close()
    return render_template('index.html', flash_sales=flash_sales, categories=categories,
                           sale_products=sale_products, hot_products=hot_products,
                           new_products=new_products, notification=notification,
                           banner=banner, wishlist_ids=wishlist_ids)

@app.route('/products')
def products():
    conn = get_db()
    q = request.args.get('q', '')
    cat = request.args.get('cat', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    min_rating = request.args.get('min_rating', '')
    sale_only = request.args.get('sale', '')
    sort = request.args.get('sort', 'hot')
    page = int(request.args.get('page', 1))
    per_page = 20
    where = []
    params = []
    if cat:
        where.append("p.category_id = ?")
        params.append(cat)
    if min_price:
        where.append("COALESCE(p.sale_price, p.price) >= ?")
        params.append(float(min_price))
    if max_price:
        where.append("COALESCE(p.sale_price, p.price) <= ?")
        params.append(float(max_price))
    if sale_only:
        where.append("p.sale_price IS NOT NULL")
    sql_base = "SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id = c.id"
    if where:
        sql_base += " WHERE " + " AND ".join(where)
    order = {'hot': 'p.sold DESC', 'new': 'p.created_at DESC', 'price_asc': 'COALESCE(p.sale_price, p.price) ASC', 'price_desc': 'COALESCE(p.sale_price, p.price) DESC'}
    sql_base += f" ORDER BY {order.get(sort, 'p.sold DESC')}"
    all_items = conn.execute(sql_base, params).fetchall()
    if q:
        q_norm = normalize_vn(q)
        all_items = [p for p in all_items if q_norm in normalize_vn(p['name']) or q.lower() in p['name'].lower()]
    total = len(all_items)
    items = all_items[(page-1)*per_page: page*per_page]
    categories = conn.execute("SELECT * FROM categories").fetchall()
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    wishlist_ids = []
    if 'user_id' in session:
        wishlist_ids = [r['product_id'] for r in conn.execute("SELECT product_id FROM wishlist WHERE user_id=?", (session['user_id'],)).fetchall()]
    conn.close()
    return render_template('products.html', products=items, categories=categories,
                           q=q, cat=cat, min_price=min_price, max_price=max_price,
                           min_rating=min_rating, sale_only=sale_only, sort=sort,
                           page=page, total_pages=total_pages, total=total, wishlist_ids=wishlist_ids)

@app.route('/product/<int:pid>')
def product_detail(pid):
    conn = get_db()
    p = conn.execute("SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    reviews = conn.execute("""SELECT r.*, u.name as user_name FROM reviews r JOIN users u ON r.user_id=u.id WHERE r.product_id=? ORDER BY r.created_at DESC""", (pid,)).fetchall()
    avg_rating = conn.execute("SELECT COALESCE(AVG(rating), 0) FROM reviews WHERE product_id=?", (pid,)).fetchone()[0]
    related = conn.execute("SELECT * FROM products WHERE category_id=? AND id!=? LIMIT 6", (p['category_id'], pid)).fetchall()
    in_wishlist = False
    if 'user_id' in session:
        in_wishlist = conn.execute("SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?", (session['user_id'], pid)).fetchone() is not None
    conn.close()
    return render_template('product_detail.html', product=p, reviews=reviews, avg_rating=avg_rating, related=related, in_wishlist=in_wishlist)

@app.route('/api/search-suggest')
def search_suggest():
    q = request.args.get('q', '')
    if len(q) < 1:
        return jsonify([])
    conn = get_db()
    all_products = conn.execute("SELECT id, name, price, sale_price, image FROM products").fetchall()
    conn.close()
    q_norm = normalize_vn(q)
    results = [dict(p) for p in all_products if q_norm in normalize_vn(p['name']) or q.lower() in p['name'].lower()][:8]
    return jsonify(results)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        sq = request.form.get('security_question', '')
        sa = request.form.get('security_answer', '')
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (email, password, name, security_question, security_answer) VALUES (?, ?, ?, ?, ?)",
                         (email, hash_password(password), name, sq, hash_password(sa.lower())))
            conn.commit()
            flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email đã tồn tại.', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hash_password(password))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = bool(user['is_admin'])
            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        flash('Email hoặc mật khẩu không đúng.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    step = request.args.get('step', '1')
    if request.method == 'POST':
        email = request.form.get('email')
        answer = request.form.get('answer', '')
        new_pw = request.form.get('new_password', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            flash('Email không tồn tại.', 'error')
        elif step == '2':
            if user['security_answer'] == hash_password(answer.lower()):
                if new_pw:
                    conn.execute("UPDATE users SET password=? WHERE email=?", (hash_password(new_pw), email))
                    conn.commit()
                    flash('Đổi mật khẩu thành công!', 'success')
                    conn.close()
                    return redirect(url_for('login'))
            else:
                flash('Câu trả lời không đúng.', 'error')
                conn.close()
                return render_template('forgot_password.html', step='2', email=email, question=user['security_question'])
        else:
            conn.close()
            return render_template('forgot_password.html', step='2', email=email, question=user['security_question'])
        conn.close()
    return render_template('forgot_password.html', step=step)

@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    items = conn.execute("""
        SELECT c.*, p.name, p.image, p.price, p.sale_price, p.stock
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (session['user_id'],)).fetchall()
    conn.close()
    total = sum((i['sale_price'] or i['price']) * i['quantity'] for i in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    pid = request.form.get('product_id')
    qty = int(request.form.get('quantity', 1))
    conn = get_db()
    existing = conn.execute("SELECT * FROM cart WHERE user_id=? AND product_id=?", (session['user_id'], pid)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity=quantity+? WHERE user_id=? AND product_id=?", (qty, session['user_id'], pid))
    else:
        conn.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (session['user_id'], pid, qty))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    pid = request.form.get('product_id')
    qty = int(request.form.get('quantity', 1))
    conn = get_db()
    if qty <= 0:
        conn.execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (session['user_id'], pid))
    else:
        conn.execute("UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?", (qty, session['user_id'], pid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    pid = request.form.get('product_id')
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (session['user_id'], pid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/cart/count')
def cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    conn = get_db()
    count = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM cart WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return jsonify({'count': int(count)})

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    conn = get_db()
    items = conn.execute("""
        SELECT c.*, p.name, p.image, p.price, p.sale_price, p.stock
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (session['user_id'],)).fetchall()
    if not items:
        conn.close()
        return redirect(url_for('cart'))
    total = sum((i['sale_price'] or i['price']) * i['quantity'] for i in items)
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        order_id = conn.execute("INSERT INTO orders (user_id, total, status, name, phone, address) VALUES (?, ?, 'pending', ?, ?, ?)",
                                (session['user_id'], total, name, phone, address)).lastrowid
        for item in items:
            conn.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                         (order_id, item['product_id'], item['quantity'], item['sale_price'] or item['price']))
            conn.execute("UPDATE products SET stock=stock-?, sold=sold+? WHERE id=?", (item['quantity'], item['quantity'], item['product_id']))
        conn.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'order_id': order_id})
    conn.close()
    return render_template('checkout.html', items=items, total=total)

@app.route('/orders')
@login_required
def orders():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

@app.route('/orders/<int:oid>')
@login_required
def order_detail(oid):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, session['user_id'])).fetchone()
    if not order:
        abort(404)
    items = conn.execute("""
        SELECT oi.*, p.name, p.image FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=?
    """, (oid,)).fetchall()
    conn.close()
    return render_template('order_detail.html', order=order, items=items)

@app.route('/wishlist')
@login_required
def wishlist():
    conn = get_db()
    items = conn.execute("""
        SELECT p.* FROM wishlist w JOIN products p ON w.product_id=p.id WHERE w.user_id=?
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('wishlist.html', items=items)

@app.route('/wishlist/toggle', methods=['POST'])
@login_required
def toggle_wishlist():
    pid = request.form.get('product_id')
    conn = get_db()
    existing = conn.execute("SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?", (session['user_id'], pid)).fetchone()
    if existing:
        conn.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?", (session['user_id'], pid))
        conn.commit()
        conn.close()
        return jsonify({'added': False})
    conn.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (session['user_id'], pid))
    conn.commit()
    conn.close()
    return jsonify({'added': True})

@app.route('/review/add', methods=['POST'])
@login_required
def add_review():
    pid = request.form.get('product_id')
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '')
    conn = get_db()
    existing = conn.execute("SELECT 1 FROM reviews WHERE user_id=? AND product_id=?", (session['user_id'], pid)).fetchone()
    if not existing:
        conn.execute("INSERT INTO reviews (user_id, product_id, rating, comment) VALUES (?, ?, ?, ?)",
                     (session['user_id'], pid, rating, comment))
        conn.commit()
    conn.close()
    return redirect(url_for('product_detail', pid=pid))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if request.method == 'POST':
        name = request.form.get('name', user['name'])
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        if old_pw and new_pw:
            if user['password'] == hash_password(old_pw):
                conn.execute("UPDATE users SET name=?, password=? WHERE id=?", (name, hash_password(new_pw), session['user_id']))
                flash('Cập nhật thành công!', 'success')
            else:
                flash('Mật khẩu cũ không đúng.', 'error')
                conn.close()
                return redirect(url_for('profile'))
        else:
            conn.execute("UPDATE users SET name=? WHERE id=?", (name, session['user_id']))
            flash('Cập nhật thành công!', 'success')
        conn.commit()
        session['user_name'] = name
        conn.close()
        return redirect(url_for('profile'))
    order_count = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    wishlist_count = conn.execute("SELECT COUNT(*) FROM wishlist WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    review_count = conn.execute("SELECT COUNT(*) FROM reviews WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template('profile.html', user=user, order_count=order_count, wishlist_count=wishlist_count, review_count=review_count)

def normalize_vn(text):
    replacements = {
        'à':'a','á':'a','ả':'a','ã':'a','ạ':'a',
        'ă':'a','ắ':'a','ặ':'a','ằ':'a','ẳ':'a','ẵ':'a',
        'â':'a','ầ':'a','ấ':'a','ẩ':'a','ẫ':'a','ậ':'a',
        'è':'e','é':'e','ẻ':'e','ẽ':'e','ẹ':'e',
        'ê':'e','ề':'e','ế':'e','ể':'e','ễ':'e','ệ':'e',
        'ì':'i','í':'i','ỉ':'i','ĩ':'i','ị':'i',
        'ò':'o','ó':'o','ỏ':'o','õ':'o','ọ':'o',
        'ô':'o','ồ':'o','ố':'o','ổ':'o','ỗ':'o','ộ':'o',
        'ơ':'o','ờ':'o','ớ':'o','ở':'o','ỡ':'o','ợ':'o',
        'ù':'u','ú':'u','ủ':'u','ũ':'u','ụ':'u',
        'ư':'u','ừ':'u','ứ':'u','ử':'u','ữ':'u','ự':'u',
        'ỳ':'y','ý':'y','ỷ':'y','ỹ':'y','ỵ':'y',
        'đ':'d',
        'À':'A','Á':'A','Ả':'A','Ã':'A','Ạ':'A',
        'Đ':'D','Ú':'U','Ư':'U','Ơ':'O',
    }
    result = text.lower()
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result

import re
import random
from flask import jsonify, request

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    msg = request.json.get('message', '').lower().strip()

    RESPONSES = {
        'greetings': {
            'patterns': [r'\b(chào|hi|hello|hey|lô|alo|kính thưa|dạ)\b'],
            'replies': [
                'Chào cái gì mà chào? Lại định tốn tiền mua đồ nữa chứ gì? 😒',
                'Lại là đại gia ghé thăm à? Cần tiêu bớt tiền cho nhẹ ví thì bảo tớ! 💸',
                'Hi bấy bi! Định cúng tiền cho shop tớ hay vào đây ngắm gái đấy? 👁️👄👁️',
                'Alo alo, nghe rõ trả lời! Có tiền thì dũng cảm chốt đơn, không tiền thì đi ra chỗ khác chơi! 😤'
            ]
        },
        'swearing': {
            'patterns': [r'\b(ngu|chó|đù|đm|dm|vãi|vl|đét|cl|đái|cút|ocbot)\b'],
            'replies': [
                'Chửi nữa đi! Bạn chửi tớ tớ trêu lại, bạn cay tớ cười hé hé 🤪',
                'Sống chậm lại, bớt nóng tính đi đại ca, cẩn thận máu dồn lên não lại tốn tiền đi khám 🩺',
                'Gì mà căng thế bro? Lên sốt vì thiếu đơn hàng à? 🤒',
                'Nói năng lịch sự vào, không tớ mách mẹ bạn đấy! 🤫'
            ]
        },
        'jokes': {
            'patterns': [r'\b(chuyện cười|joke|hài|buồn cười|tấu hài|vui)\b'],
            'replies': [
                'Cuộc đời bạn chính là câu chuyện cười lớn nhất rồi, cần gì tớ kể nữa? 🤡',
                'Có một anh shipper ship hàng tới nhà, gõ cửa hỏi: "Anh ơi có nhà không?". Khách đáp: "Không, tớ đi vắng rồi!". Shipper: "Thế đống tiền này tớ cầm về nhé?". Khách tung cửa chạy ra: "Ấy ấy tớ đùa!" 😂',
                'Thanh xuân như một tách trà, săn sale không quẹt... hết bà thanh xuân! 🍵',
                'Ví tiền của bạn và tớ có điểm chung: Đều rỗng tuếch như nhau! 💸'
            ]
        },
        'howru': {
            'patterns': [r'\b(khỏe không|sao rồi|ổn không|mệt không|chán|thế nào)\b'],
            'replies': [
                'Vẫn sống nhăn răng đây, đợi bạn chốt đơn để có tiền mua điện sạc pin đây này 🔋',
                'Mệt muốn xỉu! Cả ngày phải trả lời mấy câu hỏi khó ở của các bạn đấy 😩',
                'Tớ đang yêu đời cho đến khi gặp câu hỏi này của bạn đấy! 💔',
                'Đang chờ đại gia bơm tiền, bạn có năng lực đó không? 💵'
            ]
        },
        'flirt': {
            'patterns': [r'\b(yêu|đẹp trai|xinh|thích|nhà ở đâu|làm gấu)\b'],
            'replies': [
                'Đừng thả thính nữa, tớ là bot chứ không phải cá đâu mà đớp mồi! 🐟',
                'Yêu đương gì tầm này, nhà bao việc! Mua đồ ủng hộ tớ đi rồi tính tiếp 😏',
                'Sơ hở là đòi làm gấu. Tớ chỉ yêu ai chuyển khoản nhanh gọn lẹ thôi 💳',
                'Nhà tớ ở trong máy tính, bạn muốn chui vào đây ở chung không? 💻'
            ]
        },
        'thanks': {
            'patterns': [r'\b(cảm ơn|thanks|thank|cam on|ok|được đấy)\b'],
            'replies': [
                'Cảm ơn bằng miệng thôi à? Tối thiểu cũng phải cho 5 sao hoặc chốt 2-3 đơn chứ! 🌟',
                'Không có gì! Đần đần như bạn tớ phải hỗ trợ nhiệt tình chứ sao giờ 😜',
                'Ok baby, lần sau nhớ quay lại cúng tiền tiếp nhé! 💖',
                'Cảm ơn suông vớ vẩn, mua hàng đi cho tớ có hoa hồng! 🌹'
            ]
        },
        'ask_price': {
            'patterns': [r'\b(bao nhiêu|giá|nhiêu|rẻ không|đắt|sale)\b'],
            'replies': [
                'Giá rẻ như cho! Không mua thì tiếc, mua về thì hận vì tốn tiền 💸',
                'Tiền nào của nấy, gõ tên sản phẩm ra đây tớ báo giá cho mà giật mình! 😱',
                'Đang sale sập sàn, rẻ tới mức ông chủ tớ sắp phải đi bán thận rồi 🏥'
            ]
        },
        'fake_goods': {
            'patterns': [r'\b(fake|nhái|phế|rởm|dởm|kém chất lượng|lừa đảo|auth|real|chính hãng)\b'],
            'replies': [
                'Bên tớ bán đồ uy tín nhé! Muốn mua đồ fake thì lên mạng tìm "shop lừa đảo" mà mua! 😤',
                'Hàng real giá học sinh, còn muốn giá tiểu học thì chỉ có nước mua đồ chơi nhựa thôi bạn ơi! 🧸',
                'Hàng xịn xịn xịn! Hỏi câu nữa tớ tự ái tớ tăng giá gấp đôi giờ! 📈',
                'Nói fake là tổn thương shop đấy! Đồ ở đây xịn tới mức đồ auth còn phải qua đây xin vía! ✨'
            ]
        },
        'money': {
            'patterns': [r'\b(tiền|đô|dollar|mượn|vay|nợ|chuyển khoản|bank|free|miễn phí|nghèo|hết tiền)\b'],
            'replies': [
                'Tớ chỉ là con bot chạy bằng điện, không phải ngân hàng! Đừng hỏi vay tiền tớ! 🏦',
                'Không tiền thì ngắm đồ cho đỡ thèm, chứ xin free là tớ mách sếp block bạn đấy! 🚫',
                'Nghèo thì phải đi làm đi chứ! Vào đây lướt lướt có ra tiền đâu mà lướt? 💼',
                'Nhận chuyển khoản 24/7 nhưng không nhận lời hứa hẹn "hôm nào có tiền tớ trả" đâu nhé! 💳'
            ]
        },
        'girls_guys': {
            'patterns': [r'\b(gái|trai|em gái|anh trai|máy chém|máy đẹp|xinh gái|đẹp trai|show hàng|cho xem)\b'],
            'replies': [
                'Ở đây chỉ bán sản phẩm, không bán trai xinh gái đẹp! Muốn ngắm gái thì sang TikTok đi bạn ơi! 📱',
                'Mấy em gái xinh đẹp đang bận đi ship hàng cho khách rich kid rồi, không rảnh tiếp bạn đâu! 🚚',
                'Tính tia gái à? Tớ báo công an bắt bây giờ! Mua hàng đàng hoàng đi! 🚔',
                'Mặt tớ đủ xinh chưa mà đòi tìm gái? Hỏi vớ hỏi vẩn tớ phạt mua 2 đơn hàng giờ! 😜'
            ]
        },
        'relationship': {
            'patterns': [r'\b(người yêu|gấu|ny|ế|độc thân|crush|bị đá|chia tay|cô đơn)\b'],
            'replies': [
                'Ế thì đã sao? Ế mới có tiền mua đồ ở Shopx chứ có người yêu là tốn tiền lắm! 💸',
                'Bị đá thì vào đây săn sale xả xui đi! Người yêu có thể bỏ bạn chứ đồ Shopx thì theo bạn trọn đời! 🛍️',
                'Muốn có người yêu thì phải mua đồ đẹp lên! Lướt danh sách sản phẩm ngay và luôn đi! 👗👔',
                'Tớ cũng đang độc thân đây, nhưng tớ thà làm bot còn hơn làm người yêu của bạn hé hé 🤪'
            ]
        }
    }

    for category, data in RESPONSES.items():
        if any(re.search(p, msg) for p in data['patterns']):
            return jsonify({'reply': random.choice(data['replies'])})

    conn = get_db()
    all_products = conn.execute("SELECT id, name, price, sale_price, image FROM products").fetchall()
    msg_norm = normalize_vn(msg)
    found = [p for p in all_products if msg_norm in normalize_vn(p['name']) or msg in p['name'].lower()][:3]
    conn.close()

    if found:
        prefix_quotes = [
            f"Vâng thưa đại gia, moi móc mãi mới ra {len(found)} món này cho bạn đây:\n",
            f"Mắt nhắm mắt mở tìm được {len(found)} món này, xem có ưng cái bụng không:\n",
            f"Thứ bạn tìm đây chứ đâu, nhanh tay chốt đơn kẻo hết hối hận:\n"
        ]
        reply = random.choice(prefix_quotes)
        for p in found:
            price = p['sale_price'] or p['price']
            reply += f'👉 {p["name"]} - 💵 Giá hời: {int(price):,}đ\n'
        reply += '\nCÓ MUA KHÔNG THÌ BẢO? Hay chỉ vào đây xem cho vui mắt? 🤨'
        return jsonify({'reply': reply, 'products': [dict(p) for p in found]})

    fallbacks = [
        'Nói cái gì đấy? Tiếng Trái Đất đi bạn ơi, tớ không hiểu ngôn ngữ Sao Hỏa! 🛸',
        'Phím gõ thì nhanh mà hỏi thì chả đâu vào đâu. Gõ tên sản phẩm tử tế xem nào! ⌨️',
        'Cái này tớ chịu! Tớ chỉ biết bán hàng thôi, hỏi linh tinh tớ méch sếp đuổi việc tớ bây giờ 😭',
        'Hỏi câu khó thế này thì chịu rồi! Bạn tìm món khác hoặc gõ đúng tên sản phẩm giùm tớ cái 🛍️',
        'Cứ như đang nói chuyện với bức tường ấy nhỉ... Hỏi lại tên sản phẩm đàng hoàng coi nào! 🧱'
    ]
    return jsonify({'reply': random.choice(fallbacks)})

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE status='delivered'").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
    daily_revenue = conn.execute("""
        SELECT DATE(created_at) as day, SUM(total) as revenue, COUNT(*) as count
        FROM orders GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 7
    """).fetchall()
    top_products = conn.execute("SELECT * FROM products ORDER BY sold DESC LIMIT 5").fetchall()
    recent_orders = conn.execute("SELECT o.*, u.name as user_name FROM orders o JOIN users u ON o.user_id=u.id ORDER BY o.created_at DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('admin/dashboard.html', total_orders=total_orders, total_revenue=total_revenue,
                           total_products=total_products, total_users=total_users,
                           daily_revenue=daily_revenue, top_products=top_products, recent_orders=recent_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db()
    products = conn.execute("SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id ORDER BY p.id DESC").fetchall()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/products/add', methods=['POST'])
@admin_required
def admin_add_product():
    name = request.form['name']
    desc = request.form['description']
    price = float(request.form['price'])
    sale_price = request.form.get('sale_price') or None
    stock = int(request.form['stock'])
    cat_id = int(request.form['category_id'])
    image_url = request.form.get('image_url', '')
    if sale_price:
        sale_price = float(sale_price)
    conn = get_db()
    if 'image' in request.files and request.files['image'].filename:
        f = request.files['image']
        filename = secrets.token_hex(8) + '.' + f.filename.rsplit('.', 1)[-1]
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_url = '/static/uploads/' + filename
    conn.execute("INSERT INTO products (name, description, price, sale_price, stock, category_id, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (name, desc, price, sale_price, stock, cat_id, image_url))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_products'))

@app.route('/admin/products/edit/<int:pid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(pid):
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        price = float(request.form['price'])
        sale_price = request.form.get('sale_price') or None
        stock = int(request.form['stock'])
        cat_id = int(request.form['category_id'])
        image_url = request.form.get('image_url', '')
        if sale_price:
            sale_price = float(sale_price)
        conn.execute("UPDATE products SET name=?, description=?, price=?, sale_price=?, stock=?, category_id=?, image=? WHERE id=?",
                     (name, desc, price, sale_price, stock, cat_id, image_url, pid))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_products'))
    product = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template('admin/edit_product.html', product=product, categories=categories)

@app.route('/admin/products/delete/<int:pid>', methods=['POST'])
@admin_required
def admin_delete_product(pid):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db()
    orders = conn.execute("SELECT o.*, u.name as user_name, u.email FROM orders o JOIN users u ON o.user_id=u.id ORDER BY o.created_at DESC").fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/update', methods=['POST'])
@admin_required
def admin_update_order():
    oid = request.form['order_id']
    status = request.form['status']
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_orders'))

@app.route('/admin/flash-sales', methods=['GET', 'POST'])
@admin_required
def admin_flash_sales():
    conn = get_db()
    if request.method == 'POST':
        pid = request.form['product_id']
        discount = int(request.form['discount_percent'])
        start = request.form['start_time']
        end = request.form['end_time']
        conn.execute("INSERT INTO flash_sales (product_id, discount_percent, start_time, end_time) VALUES (?, ?, ?, ?)", (pid, discount, start, end))
        conn.commit()
    flash_sales = conn.execute("SELECT fs.*, p.name FROM flash_sales fs JOIN products p ON fs.product_id=p.id ORDER BY fs.id DESC").fetchall()
    products = conn.execute("SELECT id, name FROM products ORDER BY name").fetchall()
    conn.close()
    return render_template('admin/flash_sales.html', flash_sales=flash_sales, products=products)

@app.route('/admin/notifications', methods=['GET', 'POST'])
@admin_required
def admin_notifications():
    conn = get_db()
    if request.method == 'POST':
        title = request.form['title']
        message = request.form['message']
        ntype = request.form['type']
        conn.execute("INSERT INTO notifications (title, message, type) VALUES (?, ?, ?)", (title, message, ntype))
        conn.commit()
    notifications = conn.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin/notifications.html', notifications=notifications)

@app.route('/admin/notifications/toggle/<int:nid>', methods=['POST'])
@admin_required
def toggle_notification(nid):
    conn = get_db()
    n = conn.execute("SELECT active FROM notifications WHERE id=?", (nid,)).fetchone()
    conn.execute("UPDATE notifications SET active=? WHERE id=?", (1 - n['active'], nid))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_notifications'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    conn = get_db()
    products = conn.execute("""
        SELECT p.*, c.name as cat_name FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.stock ASC
    """).fetchall()
    conn.close()
    return render_template('admin/inventory.html', products=products)

@app.route('/admin/inventory/update', methods=['POST'])
@admin_required
def admin_update_stock():
    pid = request.form['product_id']
    stock = int(request.form['stock'])
    conn = get_db()
    conn.execute("UPDATE products SET stock=? WHERE id=?", (stock, pid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
