# Archivo: src/models/ModelProducto.py

from src.models.entities.Productos import Producto

class ModelProducto:
    
    @classmethod
    def get_all(cls, db):
        """
        Obtiene todos los productos de la base de datos
        
        Args:
            db: Conexión a la base de datos MySQL
            
        Returns:
            List[Producto]: Lista de objetos Producto
        """
        try:
            cursor = db.connection.cursor()
            sql = """SELECT id_producto, nombre, descripcion, precio, imagen, 
                            id_categoria, id_vendedor, disponible, 
                            es_personalizable, calificacion_promedio 
                     FROM productos
                     ORDER BY nombre"""
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id_producto=row[0],
                    nombre=row[1], 
                    descripcion=row[2], 
                    precio=row[3], 
                    imagen=row[4],
                    id_categoria=row[5], 
                    id_vendedor=row[6], 
                    disponible=row[7], 
                    es_personalizable=row[8], 
                    calificacion_promedio=row[9]
                )
                # Agregar stock como alias de disponible
                producto.stock = producto.disponible
                productos.append(producto)
            
            cursor.close()
            return productos
            
        except Exception as ex:
            print(f"Error en get_all: {ex}")
            raise Exception(f"Error al obtener productos: {ex}")

    @classmethod
    def get_by_id(cls, db, id_producto):
        """
        Obtiene un producto específico por su ID
        
        Args:
            db: Conexión a la base de datos MySQL
            id_producto: ID del producto a buscar
            
        Returns:
            Producto: Objeto Producto o None si no se encuentra
        """
        try:
            cursor = db.connection.cursor()
            sql = """SELECT id_producto, nombre, descripcion, precio, imagen, 
                            id_categoria, id_vendedor, disponible, 
                            es_personalizable, calificacion_promedio 
                     FROM productos 
                     WHERE id_producto = %s"""
            cursor.execute(sql, (id_producto,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                producto = Producto(
                    id_producto=row[0],
                    nombre=row[1], 
                    descripcion=row[2], 
                    precio=row[3], 
                    imagen=row[4],
                    id_categoria=row[5], 
                    id_vendedor=row[6], 
                    disponible=row[7], 
                    es_personalizable=row[8], 
                    calificacion_promedio=row[9]
                )
                # Agregar stock como alias de disponible
                producto.stock = producto.disponible
                return producto
            return None
            
        except Exception as ex:
            print(f"Error en get_by_id: {ex}")
            raise Exception(f"Error al obtener producto {id_producto}: {ex}")

    @classmethod
    def get_by_categoria(cls, db, id_categoria):
        """
        Obtiene productos por categoría
        
        Args:
            db: Conexión a la base de datos MySQL
            id_categoria: ID de la categoría
            
        Returns:
            List[Producto]: Lista de productos de la categoría
        """
        try:
            cursor = db.connection.cursor()
            sql = """SELECT id_producto, nombre, descripcion, precio, imagen, 
                            id_categoria, id_vendedor, disponible, 
                            es_personalizable, calificacion_promedio 
                     FROM productos 
                     WHERE id_categoria = %s AND disponible = 1
                     ORDER BY nombre"""
            cursor.execute(sql, (id_categoria,))
            rows = cursor.fetchall()
            cursor.close()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id_producto=row[0],
                    nombre=row[1], 
                    descripcion=row[2], 
                    precio=row[3], 
                    imagen=row[4],
                    id_categoria=row[5], 
                    id_vendedor=row[6], 
                    disponible=row[7], 
                    es_personalizable=row[8], 
                    calificacion_promedio=row[9]
                )
                # Agregar stock como alias de disponible
                producto.stock = producto.disponible
                productos.append(producto)
            
            return productos
            
        except Exception as ex:
            print(f"Error en get_by_categoria: {ex}")
            raise Exception(f"Error al obtener productos de categoría {id_categoria}: {ex}")

    @classmethod
    def search(cls, db, termino):
        """
        Busca productos por término en nombre o descripción
        
        Args:
            db: Conexión a la base de datos MySQL
            termino: Término de búsqueda
            
        Returns:
            List[Producto]: Lista de productos que coinciden con la búsqueda
        """
        try:
            cursor = db.connection.cursor()
            sql = """SELECT id_producto, nombre, descripcion, precio, imagen, 
                            id_categoria, id_vendedor, disponible, 
                            es_personalizable, calificacion_promedio 
                     FROM productos 
                     WHERE (nombre LIKE %s OR descripcion LIKE %s) 
                     AND disponible = 1
                     ORDER BY nombre"""
            termino_busqueda = f"%{termino}%"
            cursor.execute(sql, (termino_busqueda, termino_busqueda))
            rows = cursor.fetchall()
            cursor.close()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id_producto=row[0],
                    nombre=row[1], 
                    descripcion=row[2], 
                    precio=row[3], 
                    imagen=row[4],
                    id_categoria=row[5], 
                    id_vendedor=row[6], 
                    disponible=row[7], 
                    es_personalizable=row[8], 
                    calificacion_promedio=row[9]
                )
                # Agregar stock como alias de disponible
                producto.stock = producto.disponible
                productos.append(producto)
            
            return productos
            
        except Exception as ex:
            print(f"Error en search: {ex}")
            raise Exception(f"Error al buscar productos: {ex}")

    @classmethod
    def update_stock(cls, db, id_producto, nuevo_stock):
        """
        Actualiza el stock (disponible) de un producto
        
        Args:
            db: Conexión a la base de datos MySQL
            id_producto: ID del producto
            nuevo_stock: Nuevo valor del stock
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            cursor = db.connection.cursor()
            sql = "UPDATE productos SET disponible = %s WHERE id_producto = %s"
            cursor.execute(sql, (nuevo_stock, id_producto))
            db.connection.commit()
            cursor.close()
            return True
            
        except Exception as ex:
            print(f"Error al actualizar stock: {ex}")
            return False
        
    @classmethod
    def update(cls, db, id_producto, nombre, precio, disponible, es_personalizable, id_categoria, imagen):
        try:
            cursor = db.connection.cursor()
            sql = """UPDATE productos
                     SET nombre=%s, precio=%s, disponible=%s, 
                         es_personalizable=%s, id_categoria=%s, imagen=%s
                     WHERE id_producto=%s"""
            cursor.execute(sql, (nombre, precio, disponible, es_personalizable, id_categoria, imagen, id_producto))
            db.connection.commit()
            cursor.close()
            return True
        except Exception as ex:
            print(f"Error al actualizar producto: {ex}")
            db.connection.rollback()
            return False

    @staticmethod
    def delete(db, id_producto):
        try:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM productos WHERE id_producto = %s", (id_producto,))
            db.connection.commit()
            filas_eliminadas = cursor.rowcount
            cursor.close()
            return filas_eliminadas > 0
        except Exception as e:
            print(f"Error al eliminar producto: {e}")
            return False
