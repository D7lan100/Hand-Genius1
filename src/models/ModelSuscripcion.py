from datetime import datetime
import MySQLdb.cursors
from src.models.entities.Suscripcion import Suscripcion  # ✅ importa tu entidad

class ModelSuscripcion:

    # 📋 Listar todas las suscripciones con información de usuario y tipo
    @classmethod
    def listar_suscripciones(cls, db):
        try:
            cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
            sql = """
                SELECT 
                    s.id_suscripcion,
                    u.nombre_completo AS nombre_usuario,
                    ts.nombre_tipo AS tipo_suscripcion,
                    s.fecha_inicio,
                    s.fecha_fin,
                    s.comprobante,
                    s.estado
                FROM suscripciones s
                INNER JOIN usuarios u ON s.id_usuario = u.id_usuario
                INNER JOIN tipos_suscripcion ts ON s.id_tipo_suscripcion = ts.id_tipo_suscripcion
                ORDER BY s.fecha_inicio DESC
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as ex:
            raise Exception(f"Error al listar suscripciones: {ex}")

    # 📤 Actualizar comprobante de una suscripción
    @classmethod
    def actualizar_comprobante(cls, db, id_suscripcion, filename):
        try:
            cursor = db.connection.cursor()
            sql = "UPDATE suscripciones SET comprobante = %s, estado = 'Pendiente' WHERE id_suscripcion = %s"
            cursor.execute(sql, (filename, id_suscripcion))
            db.connection.commit()
            cursor.close()
            return True
        except Exception as ex:
            db.connection.rollback()
            raise Exception(f"Error al actualizar comprobante: {ex}")

    # ✅ Cambiar estado de una suscripción (Aprobada / Rechazada)
    @classmethod
    def cambiar_estado(cls, db, id_suscripcion, nuevo_estado):
        try:
            cursor = db.connection.cursor()
            sql = "UPDATE suscripciones SET estado = %s WHERE id_suscripcion = %s"
            cursor.execute(sql, (nuevo_estado, id_suscripcion))
            db.connection.commit()
            cursor.close()
            return True
        except Exception as ex:
            db.connection.rollback()
            raise Exception(f"Error al cambiar estado: {ex}")

    # 💰 Calcular ingresos del mes (solo de suscripciones aprobadas)
    @classmethod
    def ingresos_mes(cls, db):
        try:
            cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
            sql = """
                SELECT IFNULL(SUM(ts.precio), 0) AS ingresos
                FROM suscripciones s
                INNER JOIN tipos_suscripcion ts ON s.id_tipo_suscripcion = ts.id_tipo_suscripcion
                WHERE s.estado = 'Aprobada'
                AND MONTH(s.fecha_inicio) = MONTH(CURDATE())
                AND YEAR(s.fecha_inicio) = YEAR(CURDATE())
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            return result['ingresos'] if result else 0
        except Exception as ex:
            raise Exception(f"Error al obtener ingresos del mes: {ex}")

    # 🕒 Obtener suscripciones recientes (últimos 30 días)
    @classmethod
    def recientes(cls, db):
        try:
            cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
            sql = """
                SELECT 
                    u.nombre_completo AS usuario,
                    ts.nombre_tipo AS tipo,
                    s.fecha_inicio,
                    s.estado
                FROM suscripciones s
                INNER JOIN usuarios u ON s.id_usuario = u.id_usuario
                INNER JOIN tipos_suscripcion ts ON s.id_tipo_suscripcion = ts.id_tipo_suscripcion
                WHERE s.fecha_inicio >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY s.fecha_inicio DESC
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as ex:
            raise Exception(f"Error al obtener suscripciones recientes: {ex}")
        
    # 🔒 Validar suscripciones vencidas
    @classmethod
    def validar_vencidas(cls, db):
        try:
            cursor = db.connection.cursor()
            sql = """
                UPDATE suscripciones
                SET estado = 'Vencida'
                WHERE fecha_fin < CURDATE() AND estado != 'Vencida'
            """
            cursor.execute(sql)
            db.connection.commit()
            cursor.close()
            return True
        except Exception as ex:
            db.connection.rollback()
            raise Exception(f"Error al validar suscripciones vencidas: {ex}")
        
    # 🧾 Obtener la última suscripción del usuario
    @classmethod
    def get_last_by_user(cls, db, id_usuario):
        try:
            cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("""
                SELECT * FROM suscripciones
                WHERE id_usuario = %s
                ORDER BY fecha_inicio DESC
                LIMIT 1
            """, (id_usuario,))
            result = cursor.fetchone()
            cursor.close()

            # ✅ Convertimos el resultado en una instancia de la clase Suscripcion
            if result:
                return Suscripcion(**result)
            return None

        except Exception as ex:
            raise Exception(f"Error al obtener la última suscripción del usuario: {ex}")
        
    @classmethod
    def insert(cls, db, suscripcion):
        try:
            cursor = db.connection.cursor()
            sql = """
                INSERT INTO suscripciones (id_usuario, id_tipo_suscripcion, fecha_inicio, fecha_fin, comprobante, estado)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                suscripcion.id_usuario,
                suscripcion.id_tipo_suscripcion,
                suscripcion.fecha_inicio,
                suscripcion.fecha_fin,
                suscripcion.comprobante,
                suscripcion.estado
            )
            cursor.execute(sql, values)
            db.connection.commit()
            cursor.close()
            return True
        except Exception as ex:
            db.connection.rollback()
            raise Exception(f"Error al insertar suscripción: {ex}")

