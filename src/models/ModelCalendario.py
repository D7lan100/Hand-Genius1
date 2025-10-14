from .entities.Calendario import Calendario

class ModelCalendario:
    @classmethod
    def get_all(cls, db, id_usuario):
        try:
            cursor = db.connection.cursor()
            sql = """SELECT id_evento, nombre_evento, descripcion, fecha_evento
                     FROM calendario
                     WHERE id_usuario = %s"""
            cursor.execute(sql, (id_usuario,))
            rows = cursor.fetchall()
            eventos = []
            for row in rows:
                eventos.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "start": str(row[3])
                })
            return eventos
        except Exception as e:
            print("Error al obtener eventos:", e)
            return []
    
    @classmethod
    def add_event(cls, db, evento):
        try:
            cursor = db.connection.cursor()
            sql = """INSERT INTO calendario (nombre_evento, descripcion, fecha_evento, id_usuario)
                     VALUES (%s, %s, %s, %s)"""
            cursor.execute(sql, (evento.nombre_evento, evento.descripcion, evento.fecha_evento, evento.id_usuario))
            db.connection.commit()
            return True
        except Exception as e:
            print("Error al insertar evento:", e)
            return False
