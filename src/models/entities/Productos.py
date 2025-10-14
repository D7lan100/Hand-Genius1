# Archivo: src/models/entities/Productos.py

class Producto:
    def __init__(self, id_producto, nombre, descripcion, precio, imagen, 
                 id_categoria, id_vendedor, disponible, es_personalizable, calificacion_promedio):
        """
        Constructor de la clase Producto
        
        Args:
            id_producto: ID único del producto
            nombre: Nombre del producto
            descripcion: Descripción del producto
            precio: Precio del producto
            imagen: URL o path de la imagen
            id_categoria: ID de la categoría
            id_vendedor: ID del vendedor
            disponible: Bool indicando si está disponible
            es_personalizable: Bool indicando si es personalizable
            calificacion_promedio: Calificación promedio del producto
        """
        # SOLUCIÓN: Crear tanto 'id' como 'id_producto'
        # Esto permite que funcione tanto en plantillas como en el resto del código
        self.id = id_producto           # Para las plantillas HTML (producto.id)
        self.id_producto = id_producto  # Para consistencia con base de datos
        
        # Resto de atributos
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.imagen = imagen
        self.id_categoria = id_categoria
        self.id_vendedor = id_vendedor
        self.disponible = disponible
        self.es_personalizable = es_personalizable
        self.calificacion_promedio = calificacion_promedio

    def __repr__(self):
        """Representación string para debugging"""
        return f"<Producto {self.id}: {self.nombre}>"
    
    def __str__(self):
        """Representación string amigable"""
        return self.nombre
    
    def to_dict(self):
        """Convierte el objeto a diccionario (útil para JSON/APIs)"""
        return {
            'id': self.id,
            'id_producto': self.id_producto,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'imagen': self.imagen,
            'id_categoria': self.id_categoria,
            'id_vendedor': self.id_vendedor,
            'disponible': self.disponible,
            'es_personalizable': self.es_personalizable,
            'calificacion_promedio': self.calificacion_promedio
        }
    
    def get_precio_formateado(self):
        """Retorna el precio formateado con símbolo de moneda"""
        return f"${self.precio:,.2f}"
    
    def esta_disponible(self):
        """Retorna si el producto está disponible"""
        return bool(self.disponible)