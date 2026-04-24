from app import init_db

if __name__ == '__main__':
    init_db(force_reset=True)
    print('数据库已重置为初始数据。')
