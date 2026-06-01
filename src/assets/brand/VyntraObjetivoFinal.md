Este documento consolida la arquitectura relacional definitiva, las reglas de negocio, el modelo de datos y la hoja de ruta técnica para el nuevo backend modular de **Vyntra Academic**, migrado desde la infraestructura monolítica original hacia un SaaS escalable en **Supabase (PostgreSQL)**.

## 1. Identidad del Sistema y Modelo de Negocio

- **Nombre de la Plataforma:** `Solaris Academic` (Web / Administración / Profesores).
    
- **Nombre de la Aplicación Móvil:** `Solaris Go` o `Solara App` (Para Estudiantes, Profesores y Acudientes, con soporte de notificaciones push).
    
- **Modelo de Distribución (SaaS Multi-Nivel):** El sistema está diseñado para operar bajo un esquema de suscripción por niveles de pago:
    
    - _Plan Básico / Estándar:_ Autenticación basada en el número de documento de identidad (Tarjeta de Identidad o Cédula). Gestión en memoria para ciertos módulos heredados.
        
    - _Plan Premium:_ Soporte para correos institucionales (ej: `usuario@colegio.edu.co`) e integraciones avanzadas de seguridad.
        

## 2. Pilares de la Lógica de Negocio y Reglas Académicas

### A. Núcleo Académico Maleable (ABP Dinámico y Tradicional)

El sistema debe ser capaz de adaptarse a colegios tradicionales, mixtos o 100% enfocados en la metodología de **Aprendizaje Basado en Proyectos (ABP / PBL)**.

- **Escala Estricta:** Las notas se evalúan numéricamente en un rango de `0.0` a `5.0`. El umbral mínimo de aprobación es de **`3.5`**.
    
- **Estados y Colores Visuales:**
    
    - `≥ 4.0` → **Sobresaliente** (`green` / Verde).
        
    - `3.5 a 4.0` → **Aceptable** (`gold` / Oro).
        
    - `< 3.5` → **En Riesgo** (`red` / Rojo).
        
- **Propagación de Notas ABP:** Las materias y cursos se configuran anualmente de manera dinámica. Si una asignatura está marcada con el switch `is_abp = True`, la actualización o asentamiento de la nota de un proyecto transversal se propagará automáticamente a las **9 materias vinculadas** en tiempo real mediante disparadores de base de datos (_Database Triggers_).
    
- **Flexibilidad Independiente:** El sistema soporta materias "No-ABP" que se califican individualmente, e incluso permite apagar la metodología por completo en bimestres o años lectivos específicos.
    

### B. Control Financiero Inteligente (Regla de Mora y Bypass)

- **Restricción por Antigüedad:** El sistema bloquea de manera automatizada la descarga de reportes/boletines en formato PDF (generados con ReportLab) y la presentación de exámenes en línea a los estudiantes que presenten saldos pendientes de **dos (2) meses o más**.
    
- **Bypass de Rectoría:** El rol de administrador de mayor jerarquía (`Rector`) cuenta con un switch de anulación financiera global (`financial_override`). Al activarse, permite al estudiante ingresar a sus pruebas y descargar boletines aunque la base de datos registre deuda activa, agilizando acuerdos internos sin alterar el estado contable.
    
- **Preparación para Pasarela de Pagos (Wompi Ready):** El modelo almacena referencias nativas (`customer_id`, `transaction_ref`) para automatizar la conciliación mediante webhooks en fases posteriores del despliegue.
    

### C. Resiliencia ante Cortes de Energía (Exámenes Seguros)

Dada la infraestructura física en Sogamoso, el sistema está blindado contra fallas eléctricas o pérdidas de conectividad.

- **Guardado en Estado de Borrador (_Real-Time Drafts_):** Cada interacción o click del estudiante en una opción de examen se envía asíncronamente y se almacena en una estructura JSONB en la base de datos.
    
- **Reportes No-Punitivos:** Si se interrumpe la sesión abruptamente, el estado de la prueba se almacena como `'interrupted'`. El sistema despacha automáticamente un `IncidentReport` tipificado como _"Posible fallo técnico (Corte de fluido/red)"_, evitando que el estudiante pierda sus respuestas previas y permitiendo al docente reactivar el intento sin penalizaciones.
    

## 3. Modelo de Datos Relacional Completo (PostgreSQL - Supabase)

El esquema de la base de datos se ha diseñado para garantizar la integridad referencial (eliminando datos huérfanos), velocidad de consulta y soporte óptimo para **Agentes de IA Agéntica**, los cuales consumirán y manipularán estos datos mediante llamadas estructuradas a funciones (_Tools_).

SQL

```
-- Extensiones requeridas para IDs criptográficos
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Perfiles de Usuarios Centralizados (Soporta T.I. y Correo Institucional)
CREATE TABLE profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    login_credential VARCHAR(100) UNIQUE NOT NULL, -- Tarjeta de Identidad (Básico) o Email (Premium)
    fullname VARCHAR(150) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('admin', 'teacher', 'student')) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Cursos Dinámicos por Año Escolar (Ej: 11-A, 2026)
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(20) NOT NULL,
    academic_year INTEGER NOT NULL,
    description TEXT, -- Enfoque o metas anuales del grado
    director_id UUID REFERENCES profiles(id) ON DELETE SET NULL, -- Profesor titular
    UNIQUE(name, academic_year)
);

-- 3. Información Detallada del Estudiante y Estado Financiero (Control de Mora)
CREATE TABLE student_metadata (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE PRIMARY KEY,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    months_in_arrears INTEGER DEFAULT 0 CHECK (months_in_arrears >= 0),
    financial_override BOOLEAN DEFAULT FALSE, -- El botón de bypass del Rector
    wompi_customer_id VARCHAR(100),
    birth_date DATE,
    blood_type VARCHAR(5),
    guardian_name VARCHAR(150),
    guardian_phone VARCHAR(20),
    medical_notes TEXT, -- Apartado de información crucial para el chatbot de la App o el docente
    is_active BOOLEAN DEFAULT TRUE
);

-- 4. Información Profesional de los Docentes
CREATE TABLE teacher_metadata (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE PRIMARY KEY,
    specialty VARCHAR(100), -- Ej: "Licenciado en Lenguas", "Ingeniero de Sistemas"
    bio TEXT, -- Descripción de su enfoque pedagógico o experiencia
    office_hours VARCHAR(100) -- Horario de atención a acudientes
);

-- 5. Banco de Asignaturas / Materias
CREATE TABLE subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT, -- ¿De qué trata la materia? Consumible por la App y la IA
    syllabus JSONB, -- Estructura flexible para logros y temarios por periodos
    is_abp BOOLEAN DEFAULT TRUE
);

-- 6. Matriz de Asignaciones (Un profesor maneja múltiples materias en múltiples cursos)
CREATE TABLE teacher_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE(teacher_id, subject_id, course_id)
);

-- 7. Sistema Dinámico de Horarios
CREATE TABLE class_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 1 AND 5), -- 1: Lunes, 5: Viernes
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

-- 8. Recordatorios de Tareas y Agenda Escolar (App Móvil)
CREATE TABLE homework_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Persistencia de Respuestas de Exámenes en Tiempo Real (Resiliencia Eléctrica)
CREATE TABLE exam_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    exam_id UUID NOT NULL, 
    current_responses JSONB DEFAULT '{}'::jsonb, -- Guarda clics en tiempo real
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'interrupted')),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. Historial Académico Consolidado (Anualización e Históricos Rápidos)
CREATE TABLE academic_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    grade_name VARCHAR(20) NOT NULL,
    final_average NUMERIC(3,2) CHECK (final_average BETWEEN 0.0 AND 5.0),
    observations TEXT
);

-- 11. Registro de Dispositivos Móviles (Notificaciones Push de Solaris Go)
CREATE TABLE mobile_push_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL UNIQUE,
    device_type VARCHAR(20) CHECK (device_type IN ('ios', 'android')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 4. Próximos Pasos de la Hoja de Ruta Técnica

1. **Inicialización de Base de Datos:** Ejecutar el script anterior en la consola SQL de la instancia de Supabase asignada al proyecto.
    
2. **Configuración de Conexión Asíncrona:** Crear el archivo `backend/config/database.py` utilizando la librería oficial `supabase-py` configurando accesos asíncronos para FastAPI.
    
3. **Refactorización de Modelos Pydantic v2:** Crear el archivo `backend/models/auth.py` y `backend/models/schemas.py` mapeando los campos relacionales, las validaciones de notas de `0.0` a `5.0` y exponiendo todo en el paquete raíz mediante `__init__.py` para disolver los errores de importación en Render.
    
4. **Integración de la Capa de Agentes de IA:** Programar los contratos de herramientas (_tool-calling_) para que las lógicas conversacionales puedan leer y escribir en este esquema PostgreSQL de manera transparente y segura.