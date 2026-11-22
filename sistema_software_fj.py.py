"""
Sistema Integral de Gestión de Clientes, Servicios y Reservas - Software FJ
Curso: Programación (213023) - UNAD | Fase 4

Características implementadas:
- Arquitectura POO sin bases de datos: gestión con listas en memoria y registro en archivo de log.
- Clase abstracta general (EntidadBase) y clase abstracta Servicio.
- Clase Cliente con encapsulación y validaciones estrictas.
- Tres servicios especializados (ReservaSala, AlquilerEquipo, AsesoriaEspecializada) con polimorfismo.
- Sobrecarga de métodos para cálculo de costos (parámetros opcionales + @singledispatchmethod).
- Clase Reserva con gestión de estados, confirmación, cancelación y procesamiento.
- Excepciones personalizadas, bloques try/except/else/finally y encadenamiento (raise ... from ...).
- Simulación de más de 10 operaciones completas (válidas e inválidas) manteniendo el sistema activo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from functools import singledispatchmethod
import logging
from pathlib import Path
import re
from typing import Any


# ==============================================================================
# 1. CONFIGURACIÓN DEL ARCHIVO DE LOGS (EVENTOS Y ERRORES)
# ==============================================================================

LOG_FILE = Path("software_fj.log")


def configurar_logger() -> logging.Logger:
    """Configura un logger que guarda eventos y errores en archivo sin detener el sistema."""
    logger = logging.getLogger("SoftwareFJLogger")
    logger.setLevel(logging.INFO)

    # Evita duplicar handlers si se reconfigura el logger
    if not logger.handlers:
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setFormatter(formato)
        logger.addHandler(file_handler)

    return logger


logger = configurar_logger()


# ==============================================================================
# 2. EXCEPCIONES PERSONALIZADAS
# ==============================================================================

class ErrorSoftwareFJ(Exception):
    """Excepción base del sistema Software FJ."""

    def __init__(self, mensaje: str, codigo: str = "ERR_GENERAL") -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.timestamp = datetime.now().isoformat(timespec="seconds")


class ErrorDatosInvalidos(ErrorSoftwareFJ):
    """Se lanza cuando un dato no cumple con las reglas de validación o falta un parámetro."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, codigo="ERR_DATOS_INVALIDOS")


class ErrorServicioNoDisponible(ErrorSoftwareFJ):
    """Se lanza cuando un servicio no está disponible o no puede atenderse."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, codigo="ERR_SERVICIO_NO_DISPONIBLE")


class ErrorOperacionReserva(ErrorSoftwareFJ):
    """Se lanza ante transiciones de estado inválidas o fallos al procesar una reserva."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, codigo="ERR_OPERACION_RESERVA")


class ErrorCalculoFinanciero(ErrorSoftwareFJ):
    """Se lanza cuando ocurre un cálculo inconsistente o un valor financiero inválido."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, codigo="ERR_CALCULO_FINANCIERO")


# ==============================================================================
# 3. CLASE ABSTRACTA GENERAL (ENTIDADES DEL SISTEMA)
# ==============================================================================

class EntidadBase(ABC):
    """Clase abstracta base para entidades gestionadas en Software FJ."""

    def __init__(self, id_entidad: str) -> None:
        if not isinstance(id_entidad, str) or not id_entidad.strip():
            raise ErrorDatosInvalidos("El ID de la entidad debe ser un texto no vacío.")
        self._id_entidad = id_entidad.strip().upper()
        self._fecha_creacion = datetime.now()

    @property
    def id_entidad(self) -> str:
        """Retorna el identificador único de la entidad."""
        return self._id_entidad

    @property
    def fecha_creacion(self) -> datetime:
        """Retorna la fecha de creación de la entidad."""
        return self._fecha_creacion

    @abstractmethod
    def resumen(self) -> str:
        """Retorna una descripción resumida de la entidad."""


# ==============================================================================
# 4. CLASE CLIENTE (ENCAPSULACIÓN Y VALIDACIONES ESTRICTAS)
# ==============================================================================

class Cliente(EntidadBase):
    """Representa un cliente de Software FJ con datos encapsulados y validados."""

    _REGEX_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, id_cliente: str, nombre: str, correo: str, telefono: str) -> None:
        super().__init__(id_cliente)
        # Se asignan vía properties para ejecutar validaciones desde el inicio
        self.nombre = nombre
        self.correo = correo
        self.telefono = telefono

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ErrorDatosInvalidos(
                "El nombre del cliente debe ser un texto de al menos 3 caracteres."
            )
        self._nombre = valor.strip()

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        if not isinstance(valor, str) or not self._REGEX_CORREO.match(valor.strip()):
            raise ErrorDatosInvalidos(f"Correo electrónico inválido: '{valor}'.")
        self._correo = valor.strip().lower()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        limpio = re.sub(r"[\s\-()]", "", valor) if isinstance(valor, str) else ""
        if not limpio.isdigit() or len(limpio) < 7:
            raise ErrorDatosInvalidos(
                f"Teléfono inválido: '{valor}'. Debe contener al menos 7 dígitos."
            )
        self._telefono = limpio

    def resumen(self) -> str:
        return (
            f"Cliente[{self.id_entidad}] {self.nombre} | "
            f"Correo: {self.correo} | Tel: {self.telefono}"
        )


# ==============================================================================
# 5. CLASE ABSTRACTA SERVICIO Y SERVICIOS ESPECIALIZADOS (POLIMORFISMO)
# ==============================================================================

class Servicio(EntidadBase, ABC):
    """Clase abstracta que define el contrato común para los servicios de Software FJ."""

    def __init__(
        self,
        id_servicio: str,
        nombre: str,
        tarifa_base: float,
        disponible: bool = True,
    ) -> None:
        super().__init__(id_servicio)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorDatosInvalidos("El nombre del servicio no puede estar vacío.")
        if not isinstance(tarifa_base, (int, float)) or tarifa_base <= 0:
            raise ErrorCalculoFinanciero("La tarifa base debe ser un número mayor que 0.")
        if not isinstance(disponible, bool):
            raise ErrorDatosInvalidos("El estado de disponibilidad debe ser booleano.")

        self._nombre = nombre.strip()
        self._tarifa_base = float(tarifa_base)
        self._disponible = disponible

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    @disponible.setter
    def disponible(self, estado: bool) -> None:
        if not isinstance(estado, bool):
            raise ErrorDatosInvalidos("La disponibilidad debe ser True o False.")
        self._disponible = estado

    @abstractmethod
    def validar_parametros(self, duracion: int, **kwargs: Any) -> None:
        """Valida la duración y parámetros específicos del servicio."""

    @abstractmethod
    def calcular_costo_base(self, duracion: int, **kwargs: Any) -> float:
        """Calcula el costo del servicio antes de impuestos/descuentos."""

    @abstractmethod
    def describir_servicio(self) -> str:
        """Retorna una descripción detallada del servicio."""

    def resumen(self) -> str:
        estado_txt = "Disponible" if self._disponible else "No disponible"
        return f"{self.describir_servicio()} ({estado_txt})"

    # Sobrecarga de método mediante parámetros opcionales
    def calcular_costo(
        self,
        duracion: int,
        descuento_pct: float = 0.0,
        impuesto_pct: float = 0.0,
        **kwargs: Any,
    ) -> float:
        """
        Calcula el costo final aplicando validaciones, descuento e impuesto opcionales.
        Ejemplo de sobrecarga por argumentos opcionales.
        """
        self.validar_parametros(duracion, **kwargs)

        if not (0.0 <= descuento_pct < 100.0):
            raise ErrorCalculoFinanciero(
                f"El porcentaje de descuento ({descuento_pct}) debe estar entre 0 y < 100."
            )
        if not (0.0 <= impuesto_pct <= 100.0):
            raise ErrorCalculoFinanciero(
                f"El porcentaje de impuesto ({impuesto_pct}) debe estar entre 0 y 100."
            )

        subtotal = self.calcular_costo_base(duracion, **kwargs)
        if subtotal < 0:
            raise ErrorCalculoFinanciero("El subtotal calculado no puede ser negativo.")

        con_descuento = subtotal * (1.0 - descuento_pct / 100.0)
        total = con_descuento * (1.0 + impuesto_pct / 100.0)

        if total < 0:
            raise ErrorCalculoFinanciero("El costo total resultante es inconsistente (< 0).")

        return round(total, 2)

    # Sobrecarga adicional mediante @singledispatchmethod para distintos tipos de ajuste
    @singledispatchmethod
    def aplicar_ajuste(self, ajuste: Any, monto_actual: float) -> float:
        """Ajusta un monto según el tipo de dato recibido."""
        raise ErrorDatosInvalidos(
            f"Tipo de ajuste no soportado ({type(ajuste).__name__}). "
            "Use int/float (porcentaje) o dict ({'descuento': ..., 'impuesto': ...})."
        )

    @aplicar_ajuste.register
    def _(self, ajuste: int | float, monto_actual: float) -> float:
        """Ajusta el monto aplicando un porcentaje directo (positivo o negativo)."""
        if monto_actual < 0:
            raise ErrorCalculoFinanciero("El monto actual no puede ser negativo.")
        if ajuste <= -100:
            raise ErrorCalculoFinanciero("El ajuste porcentual no puede ser <= -100%.")
        return round(monto_actual * (1.0 + float(ajuste) / 100.0), 2)

    @aplicar_ajuste.register
    def _(self, ajuste: dict, monto_actual: float) -> float:
        """Ajusta el monto usando un diccionario con 'descuento' y/o 'impuesto'."""
        if monto_actual < 0:
            raise ErrorCalculoFinanciero("El monto actual no puede ser negativo.")
        desc = float(ajuste.get("descuento", 0.0))
        imp = float(ajuste.get("impuesto", 0.0))
        if not (0.0 <= desc < 100.0) or not (0.0 <= imp <= 100.0):
            raise ErrorCalculoFinanciero("Valores fuera de rango en diccionario de ajuste.")
        parcial = monto_actual * (1.0 - desc / 100.0)
        return round(parcial * (1.0 + imp / 100.0), 2)


class ReservaSala(Servicio):
    """Servicio especializado para reserva de salas (duración en horas)."""

    def __init__(
        self,
        id_servicio: str,
        nombre: str,
        tarifa_hora: float,
        capacidad_personas: int,
        disponible: bool = True,
    ) -> None:
        super().__init__(id_servicio, nombre, tarifa_hora, disponible)
        if not isinstance(capacidad_personas, int) or capacidad_personas <= 0:
            raise ErrorDatosInvalidos("La capacidad de la sala debe ser un entero positivo.")
        self._capacidad_personas = capacidad_personas

    @property
    def capacidad_personas(self) -> int:
        return self._capacidad_personas

    def validar_parametros(self, duracion: int, **kwargs: Any) -> None:
        if not isinstance(duracion, int) or isinstance(duracion, bool) or duracion <= 0:
            raise ErrorDatosInvalidos(
                "Para ReservaSala, la duración (horas) debe ser un entero mayor que 0."
            )
        asistentes = kwargs.get("asistentes")
        if asistentes is not None:
            if not isinstance(asistentes, int) or asistentes <= 0:
                raise ErrorDatosInvalidos("El número de asistentes debe ser positivo.")
            if asistentes > self._capacidad_personas:
                raise ErrorServicioNoDisponible(
                    f"La sala '{self.nombre}' soporta máximo {self._capacidad_personas} "
                    f"personas; se solicitaron {asistentes}."
                )

    def calcular_costo_base(self, duracion: int, **kwargs: Any) -> float:
        return self.tarifa_base * duracion

    def describir_servicio(self) -> str:
        return (
            f"ReservaSala[{self.id_entidad}] '{self.nombre}' "
            f"(Cap: {self._capacidad_personas} pers., ${self.tarifa_base:,.2f}/h)"
        )


class AlquilerEquipo(Servicio):
    """Servicio especializado para alquiler de equipos (duración en días)."""

    def __init__(
        self,
        id_servicio: str,
        nombre: str,
        tarifa_dia: float,
        cantidad_stock: int,
        disponible: bool = True,
    ) -> None:
        super().__init__(id_servicio, nombre, tarifa_dia, disponible)
        if not isinstance(cantidad_stock, int) or cantidad_stock < 0:
            raise ErrorDatosInvalidos("El stock del equipo debe ser un entero >= 0.")
        self._cantidad_stock = cantidad_stock
        if self._cantidad_stock == 0:
            self._disponible = False

    @property
    def cantidad_stock(self) -> int:
        return self._cantidad_stock

    def validar_parametros(self, duracion: int, **kwargs: Any) -> None:
        if not isinstance(duracion, int) or isinstance(duracion, bool) or duracion <= 0:
            raise ErrorDatosInvalidos(
                "Para AlquilerEquipo, la duración (días) debe ser un entero mayor que 0."
            )
        unidades = kwargs.get("unidades", 1)
        if not isinstance(unidades, int) or unidades <= 0:
            raise ErrorDatosInvalidos("Las unidades a alquilar deben ser un entero positivo.")
        if unidades > self._cantidad_stock:
            raise ErrorServicioNoDisponible(
                f"Stock insuficiente en '{self.nombre}': disponibles {self._cantidad_stock}, "
                f"solicitados {unidades}."
            )

    def calcular_costo_base(self, duracion: int, **kwargs: Any) -> float:
        unidades = kwargs.get("unidades", 1)
        return self.tarifa_base * duracion * unidades

    def describir_servicio(self) -> str:
        return (
            f"AlquilerEquipo[{self.id_entidad}] '{self.nombre}' "
            f"(Stock: {self._cantidad_stock}, ${self.tarifa_base:,.2f}/día)"
        )


class AsesoriaEspecializada(Servicio):
    """Servicio especializado para asesorías técnicas (duración en sesiones/horas)."""

    def __init__(
        self,
        id_servicio: str,
        nombre: str,
        tarifa_sesion: float,
        especialidad: str,
        disponible: bool = True,
    ) -> None:
        super().__init__(id_servicio, nombre, tarifa_sesion, disponible)
        if not isinstance(especialidad, str) or not especialidad.strip():
            raise ErrorDatosInvalidos("La especialidad de la asesoría es obligatoria.")
        self._especialidad = especialidad.strip()

    @property
    def especialidad(self) -> str:
        return self._especialidad

    def validar_parametros(self, duracion: int, **kwargs: Any) -> None:
        if not isinstance(duracion, int) or isinstance(duracion, bool) or duracion <= 0:
            raise ErrorDatosInvalidos(
                "Para AsesoriaEspecializada, la duración (sesiones) debe ser un entero > 0."
            )

    def calcular_costo_base(self, duracion: int, **kwargs: Any) -> float:
        return self.tarifa_base * duracion

    def describir_servicio(self) -> str:
        return (
            f"AsesoriaEspecializada[{self.id_entidad}] '{self.nombre}' "
            f"[{self._especialidad}] (${self.tarifa_base:,.2f}/sesión)"
        )


# ==============================================================================
# 6. CLASE RESERVA (GESTIÓN DE ESTADOS Y OPERACIONES)
# ==============================================================================

class Reserva(EntidadBase):
    """Integra un Cliente, un Servicio, duración y estado con control de excepciones."""

    ESTADOS_VALIDOS = {"PENDIENTE", "CONFIRMADA", "CANCELADA", "PROCESADA"}

    def __init__(
        self,
        id_reserva: str,
        cliente: Cliente,
        servicio: Servicio,
        duracion: int,
        descuento_pct: float = 0.0,
        impuesto_pct: float = 0.0,
        **parametros_servicio: Any,
    ) -> None:
        super().__init__(id_reserva)

        if not isinstance(cliente, Cliente):
            raise ErrorDatosInvalidos("Se requiere una instancia válida de Cliente.")
        if not isinstance(servicio, Servicio):
            raise ErrorDatosInvalidos("Se requiere una instancia válida de Servicio.")

        # Encadenamiento de excepciones si el servicio no está disponible o falla el cálculo
        try:
            if not servicio.disponible:
                raise ErrorServicioNoDisponible(
                    f"El servicio '{servicio.nombre}' ({servicio.id_entidad}) no está disponible."
                )
            costo = servicio.calcular_costo(
                duracion=duracion,
                descuento_pct=descuento_pct,
                impuesto_pct=impuesto_pct,
                **parametros_servicio,
            )
        except ErrorSoftwareFJ as exc:
            raise ErrorOperacionReserva(
                f"No se pudo crear la reserva '{self.id_entidad}' para {cliente.nombre}."
            ) from exc

        self._cliente = cliente
        self._servicio = servicio
        self._duracion = duracion
        self._parametros_servicio = parametros_servicio
        self._costo_total = costo
        self._estado = "PENDIENTE"

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_total(self) -> float:
        return self._costo_total

    def confirmar(self) -> None:
        if self._estado == "CANCELADA":
            raise ErrorOperacionReserva(
                f"No se puede confirmar la reserva {self.id_entidad}: está CANCELADA."
            )
        if self._estado == "PROCESADA":
            raise ErrorOperacionReserva(
                f"La reserva {self.id_entidad} ya fue PROCESADA."
            )
        if not self._servicio.disponible:
            raise ErrorServicioNoDisponible(
                f"El servicio {self._servicio.nombre} dejó de estar disponible."
            )
        self._estado = "CONFIRMADA"

    def cancelar(self, motivo: str = "Cancelada por solicitud") -> None:
        if self._estado == "PROCESADA":
            raise ErrorOperacionReserva(
                f"No se puede cancelar la reserva {self.id_entidad}: ya fue PROCESADA."
            )
        if self._estado == "CANCELADA":
            raise ErrorOperacionReserva(
                f"La reserva {self.id_entidad} ya se encuentra CANCELADA."
            )
        self._estado = "CANCELADA"
        logger.info(f"Reserva {self.id_entidad} cancelada. Motivo: {motivo}")

    def procesar(self) -> float:
        if self._estado == "CANCELADA":
            raise ErrorOperacionReserva(
                f"No se puede procesar la reserva {self.id_entidad}: está CANCELADA."
            )
        if self._estado != "CONFIRMADA":
            raise ErrorOperacionReserva(
                f"La reserva {self.id_entidad} debe estar CONFIRMADA antes de procesarse "
                f"(estado actual: {self._estado})."
            )
        if self._costo_total <= 0:
            raise ErrorCalculoFinanciero(
                f"Costo inválido (${self._costo_total}) al procesar reserva {self.id_entidad}."
            )
        self._estado = "PROCESADA"
        return self._costo_total

    def resumen(self) -> str:
        return (
            f"Reserva[{self.id_entidad}] Estado: {self._estado} | "
            f"Cliente: {self._cliente.nombre} | Servicio: {self._servicio.nombre} | "
            f"Duración: {self._duracion} | Total: ${self._costo_total:,.2f}"
        )


# ==============================================================================
# 7. GESTOR EN MEMORIA (LISTAS INTERNAS, SIN BASE DE DATOS)
# ==============================================================================

class GestorSoftwareFJ:
    """Administra clientes, servicios y reservas en memoria y registra eventos en log."""

    def __init__(self) -> None:
        self.clientes: list[Cliente] = []
        self.servicios: list[Servicio] = []
        self.reservas: list[Reserva] = []

    def registrar_cliente(self, cliente: Cliente) -> None:
        if any(c.id_entidad == cliente.id_entidad for c in self.clientes):
            raise ErrorDatosInvalidos(f"Ya existe un cliente con ID '{cliente.id_entidad}'.")
        self.clientes.append(cliente)

    def registrar_servicio(self, servicio: Servicio) -> None:
        if any(s.id_entidad == servicio.id_entidad for s in self.servicios):
            raise ErrorDatosInvalidos(f"Ya existe un servicio con ID '{servicio.id_entidad}'.")
        self.servicios.append(servicio)

    def crear_reserva(self, reserva: Reserva) -> None:
        if any(r.id_entidad == reserva.id_entidad for r in self.reservas):
            raise ErrorOperacionReserva(f"Ya existe una reserva con ID '{reserva.id_entidad}'.")
        self.reservas.append(reserva)


# ==============================================================================
# 8. EJECUCIÓN DE OPERACIONES Y DEMOSTRACIÓN DE EXCEPCIONES (12 OPERACIONES)
# ==============================================================================

def ejecutar_operacion(numero: int, descripcion: str, accion) -> None:
    """
    Ejecuta una operación aplicando try / except / else / finally
    y encadenamiento de excepciones cuando corresponde.
    """
    print(f"\n--- Operación #{numero}: {descripcion} ---")
    exito = False
    try:
        resultado = accion()
    except ErrorSoftwareFJ as exc:
        # Encadenamos el error de dominio hacia una excepción de control de flujo
        error_encadenado = RuntimeError(f"Fallo controlado en Op #{numero} [{exc.codigo}]")
        error_encadenado.__cause__ = exc
        logger.error(
            f"Op #{numero} ({descripcion}) falló: {exc} | Causa raíz: {type(exc).__name__}"
        )
        print(f"  [ERROR CONTROLADO] {exc}")
    except Exception as exc:
        logger.critical(f"Op #{numero} ({descripcion}) error inesperado: {exc}")
        print(f"  [ERROR INESPERADO] {exc}")
    else:
        exito = True
        logger.info(f"Op #{numero} ({descripcion}) exitosa: {resultado}")
        print(f"  [OK] {resultado}")
    finally:
        estado_op = "COMPLETADA" if exito else "FALLIDA (SISTEMA ESTABLE)"
        print(f"  [FINALLY] Operación #{numero} -> {estado_op}")


def simular_sistema() -> None:
    gestor = GestorSoftwareFJ()
    logger.info("=== INICIO DE SIMULACIÓN SOFTWARE FJ ===")

    # Referencias compartidas entre operaciones
    estado_sim: dict[str, Any] = {}

    # Op 1: Registro válido de cliente
    def op1():
        c1 = Cliente("CLI-01", "Kewin Rey", "kewin@ejemplo.com", "3105550101")
        gestor.registrar_cliente(c1)
        estado_sim["c1"] = c1
        return c1.resumen()

    # Op 2: Registro inválido de cliente (correo malo)
    def op2():
        c_bad = Cliente("CLI-02", "Ana Torres", "correo_sin_arroba", "3001234567")
        gestor.registrar_cliente(c_bad)
        return c_bad.resumen()

    # Op 3: Registro válido de segundo cliente
    def op3():
        c2 = Cliente("CLI-03", "Valentina Rojas", "val.rojas@correo.co", "3159876543")
        gestor.registrar_cliente(c2)
        estado_sim["c2"] = c2
        return c2.resumen()

    # Op 4: Creación correcta de servicios especializados (Sala, Equipo, Asesoría)
    def op4():
        s_sala = ReservaSala("SRV-SALA-1", "Sala Arquitectura", 80000.0, capacidad_personas=10)
        s_equipo = AlquilerEquipo("SRV-EQ-1", "Laptop Dev Pro", 45000.0, cantidad_stock=4)
        s_asesoria = AsesoriaEspecializada(
            "SRV-ASE-1", "Auditoría POO & Python", 120000.0, especialidad="Arquitectura Software"
        )
        gestor.registrar_servicio(s_sala)
        gestor.registrar_servicio(s_equipo)
        gestor.registrar_servicio(s_asesoria)
        estado_sim["s_sala"] = s_sala
        estado_sim["s_equipo"] = s_equipo
        estado_sim["s_asesoria"] = s_asesoria
        return f"3 servicios registrados ({s_sala.nombre}, {s_equipo.nombre}, {s_asesoria.nombre})"

    # Op 5: Creación incorrecta de servicio (tarifa negativa -> ErrorCalculoFinanciero)
    def op5():
        s_bad = ReservaSala("SRV-BAD", "Sala Error", -25000.0, capacidad_personas=5)
        gestor.registrar_servicio(s_bad)
        return s_bad.resumen()

    # Op 6: Reserva exitosa de sala con descuento e impuesto (sobrecarga por parámetros opcionales)
    def op6():
        r1 = Reserva(
            "RES-01",
            estado_sim["c1"],
            estado_sim["s_sala"],
            duracion=3,
            descuento_pct=10.0,
            impuesto_pct=19.0,
            asistentes=8,
        )
        r1.confirmar()
        total_cobrado = r1.procesar()
        gestor.crear_reserva(r1)
        estado_sim["r1"] = r1
        return f"{r1.resumen()} | Cobrado: ${total_cobrado:,.2f}"

    # Op 7: Reserva fallida por exceder capacidad de sala (encadenamiento de excepciones)
    def op7():
        r_bad = Reserva(
            "RES-02",
            estado_sim["c2"],
            estado_sim["s_sala"],
            duracion=2,
            asistentes=25,  # Excede capacidad de 10
        )
        gestor.crear_reserva(r_bad)
        return r_bad.resumen()

    # Op 8: Reserva válida de alquiler de equipo y posterior cancelación
    def op8():
        r2 = Reserva(
            "RES-03",
            estado_sim["c2"],
            estado_sim["s_equipo"],
            duracion=4,
            unidades=2,
        )
        r2.confirmar()
        r2.cancelar("Cambio de cronograma del cliente")
        gestor.crear_reserva(r2)
        estado_sim["r2"] = r2
        return r2.resumen()

    # Op 9: Intento fallido de procesar una reserva cancelada
    def op9():
        return estado_sim["r2"].procesar()

    # Op 10: Reserva válida de asesoría + prueba de sobrecarga con @singledispatchmethod
    def op10():
        r3 = Reserva(
            "RES-04",
            estado_sim["c1"],
            estado_sim["s_asesoria"],
            duracion=2,
        )
        r3.confirmar()
        r3.procesar()
        gestor.crear_reserva(r3)
        ajuste_pct = estado_sim["s_asesoria"].aplicar_ajuste(-5, r3.costo_total)
        ajuste_dict = estado_sim["s_asesoria"].aplicar_ajuste(
            {"descuento": 5.0, "impuesto": 19.0}, r3.costo_total
        )
        return (
            f"{r3.resumen()} | Ajuste -5%: ${ajuste_pct:,.2f} | "
            f"Ajuste dict: ${ajuste_dict:,.2f}"
        )

    # Op 11: Marcar servicio como no disponible e intentar crear reserva
    def op11():
        estado_sim["s_asesoria"].disponible = False
        r_nodisp = Reserva(
            "RES-05",
            estado_sim["c2"],
            estado_sim["s_asesoria"],
            duracion=1,
        )
        gestor.crear_reserva(r_nodisp)
        return r_nodisp.resumen()

    # Op 12: Validación estricta de encapsulación (intento de asignar teléfono inválido)
    def op12():
        estado_sim["c1"].telefono = "abc_no_valido"
        return estado_sim["c1"].resumen()

    operaciones = [
        (1, "Registro válido de cliente", op1),
        (2, "Registro inválido de cliente (correo)", op2),
        (3, "Registro válido de segundo cliente", op3),
        (4, "Creación correcta de 3 servicios especializados", op4),
        (5, "Creación incorrecta de servicio (tarifa negativa)", op5),
        (6, "Reserva exitosa de sala + confirmar + procesar", op6),
        (7, "Reserva fallida por exceso de capacidad", op7),
        (8, "Reserva de equipo y cancelación válida", op8),
        (9, "Intento inválido de procesar reserva cancelada", op9),
        (10, "Reserva de asesoría + sobrecarga @singledispatchmethod", op10),
        (11, "Reserva fallida por servicio no disponible", op11),
        (12, "Validación de encapsulación al modificar teléfono", op12),
    ]

    for num, desc, fn in operaciones:
        ejecutar_operacion(num, desc, fn)

    logger.info("=== FIN DE SIMULACIÓN SOFTWARE FJ ===")

    print("\n================ ESTADO FINAL EN MEMORIA ================")
    print(f"Clientes registrados : {len(gestor.clientes)}")
    print(f"Servicios registrados: {len(gestor.servicios)}")
    print(f"Reservas registradas : {len(gestor.reservas)}")
    print(f"Archivo de log       : {LOG_FILE.resolve()}")


if __name__ == "__main__":
    simular_sistema()