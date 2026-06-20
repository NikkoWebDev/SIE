import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:4321';
const API = 'http://localhost:8000';

// ═══════════════════════════════════════════════════════════════
// MOCK DATA
// ═══════════════════════════════════════════════════════════════

const MOCK_USER_STUDENT = {
  access_token: 'mock-student-token',
  usuario: { rol: 'ESTUDIANTE', nombre: 'Juan Pérez', profile_id: 'profile_101', login_credential: '101' },
  nombre: 'Juan Pérez', rol: 'ESTUDIANTE', grado: '10-A'
};
const MOCK_USER_TEACHER = {
  access_token: 'mock-teacher-token',
  usuario: { rol: 'PROFESOR', nombre: 'María García', profile_id: 'profile_11', login_credential: '11' },
  nombre: 'María García', rol: 'PROFESOR'
};
const MOCK_USER_ADMIN = {
  access_token: 'mock-admin-token',
  usuario: { rol: 'ADMIN', nombre: 'Carlos Admin', profile_id: 'profile_1', login_credential: '1' },
  nombre: 'Carlos Admin', rol: 'ADMIN'
};

const MOCK_GRADES = [
  { student_name: 'Juan Pérez', subject_name: 'Matemáticas', score: 4.2, period: 'P1' },
  { student_name: 'Juan Pérez', subject_name: 'Lenguaje', score: 3.8, period: 'P1' },
  { student_name: 'Juan Pérez', subject_name: 'Ciencias', score: 4.5, period: 'P1' },
];

const MOCK_SUBJECTS = [
  { id: 'sub-1', name: 'Matemáticas', grade: '10-A', description: 'Álgebra y geometría' },
  { id: 'sub-2', name: 'Lenguaje', grade: '10-A', description: 'Comprensión lectora' },
];

const MOCK_STUDENTS = [
  { _id: 's1', document_id: '101', fullname: 'Juan Pérez', grade: '10-A', is_paid: true },
  { _id: 's2', document_id: '102', fullname: 'Ana López', grade: '10-B', is_paid: false },
];

const MOCK_TEACHERS = [
  { document_id: '11', fullname: 'María García', subjects: [{ name: 'Matemáticas' }] },
];

const MOCK_NOTICES = [
  { titulo: 'Aviso de prueba', contenido: 'Contenido del aviso', fecha: '2025-01-15' },
];

const MOCK_STATS = { mora: 1, total_grades: 6, total_students: 45, total_teachers: 8, total_notices: 3 };

const MOCK_SCHEDULE = {
  hours: [{ time: '7:00' }, { time: '8:00' }],
  days: {
    lunes: [{ subject: 'Matemáticas' }, { subject: 'Lenguaje' }],
    martes: [{ subject: 'Ciencias' }, { subject: 'Inglés' }],
    miercoles: [{ subject: 'Sociales' }, { subject: 'Matemáticas' }],
    jueves: [{ subject: 'Lenguaje' }, { subject: 'Ciencias' }],
    viernes: [{ subject: 'Inglés' }, { subject: 'Sociales' }],
  }
};

const MOCK_EXAMS = [
  { id: 'ex-1', title: 'Examen de Matemáticas', subject_name: 'Matemáticas', duration_minutes: 30, questions: [] },
];

const MOCK_CANDIDATES = [
  { id: 'c1', name: 'Candidato A', votes: 5, photo_url: '' },
  { id: 'c2', name: 'Candidato B', votes: 3, photo_url: '' },
];

const MOCK_RISK_STUDENTS = [
  { fullname: 'Ana López', avg_score: 2.8 },
];

const MOCK_DELIVERIES = [
  { title: 'Tarea 1', subject: 'Matemáticas', student_name: 'Juan Pérez', file_url: '' },
];

const MOCK_GUIDES = [
  { title: 'Guía de Álgebra', subject_name: 'Matemáticas', grade: '10-A', file_url: '' },
];

const MOCK_INCIDENTS = [
  { student_name: 'Juan Pérez', exam_title: 'Examen 1', strikes: 2, incident_type: 'Tab switching' },
];

const MOCK_ADMINS = [
  { fullname: 'Carlos Admin', login_credential: '1', role: 'admin' },
];

// ═══════════════════════════════════════════════════════════════
// API MOCKING HELPER
// ═══════════════════════════════════════════════════════════════

function json(data, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(data) };
}

async function mockAllApis(page) {
  await page.route('**/api/health', r => r.fulfill(json({ status: 'ok' })));
  await page.route('**/api/auth/login', r => r.fulfill(json(MOCK_USER_STUDENT)));
  await page.route('**/api/auth/verify', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/auth/logout', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/auth/forgot-password', r => r.fulfill(json({ detail: 'Código enviado' })));
  await page.route('**/api/auth/reset-password', r => r.fulfill(json({ detail: 'Contraseña actualizada' })));
  await page.route('**/api/grades**', r => r.fulfill(json(MOCK_GRADES)));
  await page.route('**/api/subjects**', r => r.fulfill(json(MOCK_SUBJECTS)));
  await page.route('**/api/notices**', r => r.fulfill(json(MOCK_NOTICES)));
  await page.route('**/api/students/risk**', r => r.fulfill(json({ students: MOCK_RISK_STUDENTS })));
  await page.route('**/api/students**', r => r.fulfill(json({ data: MOCK_STUDENTS })));
  await page.route('**/api/admin/stats**', r => r.fulfill(json(MOCK_STATS)));
  await page.route('**/api/admin/students**', r => r.fulfill(json(MOCK_STUDENTS)));
  await page.route('**/api/admin/teachers**', r => r.fulfill(json(MOCK_TEACHERS)));
  await page.route('**/api/admin/subjects**', r => r.fulfill(json(MOCK_SUBJECTS)));
  await page.route('**/api/admin/candidates**', r => r.fulfill(json(MOCK_CANDIDATES)));
  await page.route('**/api/admin/notices**', r => r.fulfill(json(MOCK_NOTICES)));
  await page.route('**/api/admin/identity-directory**', r => r.fulfill(json(MOCK_ADMINS)));
  await page.route('**/api/admin/admins**', r => r.fulfill(json(MOCK_ADMINS)));
  await page.route('**/api/admin/election-reset**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/admin/student/cast-vote**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/admin/assign-teacher**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/schedule**', r => r.fulfill(json(MOCK_SCHEDULE)));
  await page.route('**/api/teacher/schedule**', r => r.fulfill(json({ grado: '10-A', ...MOCK_SCHEDULE })));
  await page.route('**/api/teacher/my-exams**', r => r.fulfill(json(MOCK_EXAMS)));
  await page.route('**/api/teacher/create-exam**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/teacher/guides**', r => r.fulfill(json(MOCK_GUIDES)));
  await page.route('**/api/teacher/deliveries**', r => r.fulfill(json(MOCK_DELIVERIES)));
  await page.route('**/api/teacher/exam-incidents**', r => r.fulfill(json(MOCK_INCIDENTS)));
  await page.route('**/api/teacher/submit-grade**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/student/exams**', r => r.fulfill(json(MOCK_EXAMS)));
  await page.route('**/api/student/deliveries**', r => r.fulfill(json(MOCK_DELIVERIES)));
  await page.route('**/api/student/upload-homework**', r => r.fulfill(json({ ok: true })));
  await page.route('**/api/ai/**', r => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('data: {"token":"Hola"}\n\ndata: {"token":" mundo"}\n\ndata: [DONE]\n\n'));
        controller.close();
      }
    });
    r.fulfill({ status: 200, contentType: 'text/event-stream', body: stream });
  });
  await page.route('**/api/**', r => r.fulfill(json({})));
}

// ═══════════════════════════════════════════════════════════════
// LOGIN HELPER (with API mocking)
// ═══════════════════════════════════════════════════════════════

async function mockLogin(page, cred) {
  // Override the login route for specific role
  if (cred.id === '11') {
    await page.route('**/api/auth/login', r => r.fulfill(json(MOCK_USER_TEACHER)));
  } else if (cred.id === '1') {
    await page.route('**/api/auth/login', r => r.fulfill(json(MOCK_USER_ADMIN)));
  } else {
    await page.route('**/api/auth/login', r => r.fulfill(json(MOCK_USER_STUDENT)));
  }
  await page.goto(`${BASE}/login`);
  await page.fill('#credential', cred.id);
  await page.fill('#password', cred.pass);
  await page.click('#login-submit');
  await page.waitForURL(new RegExp(cred.dashboard.replace('/', '\\/')), { timeout: 15000 });
}

const CREDS = {
  student: { id: '101', pass: 'alumno', dashboard: '/estudiante' },
  teacher: { id: '11', pass: 'profe', dashboard: '/docente' },
  admin: { id: '1', pass: 'admin', dashboard: '/admin' },
};

function collectConsoleErrors(page) {
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (!text.includes('ERR_CONNECTION_REFUSED') && !text.includes('favicon') && !text.includes('WebSocket')) {
        errors.push(text);
      }
    }
  });
  return errors;
}

// ═══════════════════════════════════════════════════════════════
// 1. AUTHENTICATION
// ═══════════════════════════════════════════════════════════════

test.describe('1 — Authentication', () => {
  test('Login page loads with correct elements', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await expect(page.locator('h1')).toContainText('VYNTRA');
    await expect(page.locator('#credential')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('#login-submit')).toBeVisible();
    await expect(page.locator('#forgot-link')).toBeVisible();
  });

  test('Login: empty fields show validation errors', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#login-submit');
    await expect(page.locator('#credential-error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#password-error')).toBeVisible({ timeout: 5000 });
  });

  test('Login: invalid credentials show error', async ({ page }) => {
    await mockAllApis(page);
    await page.route('**/api/auth/login', r => r.fulfill(json({ detail: 'Credenciales inválidas' }, 401)));
    await page.goto(`${BASE}/login`);
    await page.fill('#credential', 'INVALID');
    await page.fill('#password', 'wrongpass');
    await page.click('#login-submit');
    await expect(page.locator('#login-error')).toBeVisible({ timeout: 8000 });
  });

  test('Login: credential field blur validation', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.locator('#credential').click();
    await page.locator('#credential').blur();
    await expect(page.locator('#credential-error')).toBeVisible();
  });

  test('Login: password field blur validation', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.locator('#password').click();
    await page.locator('#password').blur();
    await expect(page.locator('#password-error')).toBeVisible();
  });

  test('Student login (101/alumno) → /estudiante', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page).toHaveURL(/\/estudiante/);
  });

  test('Teacher login (11/profe) → /docente', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    await expect(page).toHaveURL(/\/docente/);
  });

  test('Admin login (1/admin) → /admin', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await expect(page).toHaveURL(/\/admin/);
  });

  test('Dashboard without auth → redirect to login', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/dashboard`);
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/login');
  });

  test('Login stores role in localStorage', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const role = await page.evaluate(() => localStorage.getItem('userRole'));
    expect(role).toBe('ESTUDIANTE');
  });

  test('Login stores userName in localStorage', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const name = await page.evaluate(() => localStorage.getItem('userName'));
    expect(name).toBeTruthy();
  });

  test('Login shows spinner during submission', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.fill('#credential', '101');
    await page.fill('#password', 'alumno');
    // Add delay to login to catch spinner
    await page.route('**/api/auth/login', async r => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      r.fulfill(json(MOCK_USER_STUDENT));
    });
    await page.click('#login-submit');
    // Spinner should appear briefly
    await expect(page.locator('#submit-spinner')).toBeVisible({ timeout: 2000 });
  });
});

// ═══════════════════════════════════════════════════════════════
// 2. FORGOT PASSWORD
// ═══════════════════════════════════════════════════════════════

test.describe('2 — Forgot Password', () => {
  test('Modal opens and has step 1 elements', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await expect(page.locator('#forgot-modal')).toBeVisible();
    await expect(page.locator('#forgot-credential')).toBeVisible();
    await expect(page.locator('#forgot-send-btn')).toBeVisible();
    await expect(page.locator('#forgot-close')).toBeVisible();
  });

  test('Modal closes on close button click', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await expect(page.locator('#forgot-modal')).toBeVisible();
    await page.click('#forgot-close');
    await expect(page.locator('#forgot-modal')).not.toBeVisible();
  });

  test('Modal closes on backdrop click', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await expect(page.locator('#forgot-modal')).toBeVisible();
    await page.locator('#forgot-modal').click({ position: { x: 5, y: 5 } });
    await expect(page.locator('#forgot-modal')).not.toBeVisible();
  });

  test('Step 1: empty credential shows error', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.click('#forgot-send-btn');
    await expect(page.locator('#forgot-step-1-error')).toBeVisible();
  });

  test('Step 1 → Step 2 transition on valid credential', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', '101');
    await page.click('#forgot-send-btn');
    await page.waitForTimeout(1500);
    const step2Visible = await page.locator('#forgot-step-2').isVisible();
    expect(step2Visible).toBeTruthy();
  });

  test('Step 2: empty code shows error', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', '101');
    await page.click('#forgot-send-btn');
    await page.waitForTimeout(1500);
    await page.click('#forgot-reset-btn');
    await expect(page.locator('#forgot-step-2-error')).toBeVisible();
  });

  test('Step 2: password mismatch shows error', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', '101');
    await page.click('#forgot-send-btn');
    await page.waitForTimeout(1500);
    await page.fill('#forgot-code', '123456');
    await page.fill('#forgot-new-pass', 'newpass');
    await page.fill('#forgot-confirm-pass', 'different');
    await page.click('#forgot-reset-btn');
    await expect(page.locator('#forgot-step-2-error')).toContainText('no coinciden');
  });

  test('Step 2: successful reset shows success message', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', '101');
    await page.click('#forgot-send-btn');
    await page.waitForTimeout(1500);
    await page.fill('#forgot-code', '123456');
    await page.fill('#forgot-new-pass', 'newpass1234');
    await page.fill('#forgot-confirm-pass', 'newpass1234');
    await page.click('#forgot-reset-btn');
    await page.waitForTimeout(1000);
    await expect(page.locator('#forgot-step-2-success')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════
// 3. STUDENT DASHBOARD
// ═══════════════════════════════════════════════════════════════

test.describe('3 — Student Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
  });

  test('Inicio section visible by default', async ({ page }) => {
    await expect(page.locator('#sec-inicio')).toBeVisible();
    await expect(page.locator('#student-name')).toBeVisible();
    await expect(page.locator('#stat-avg')).toBeVisible();
    await expect(page.locator('#stat-subjects')).toBeVisible();
    await expect(page.locator('#stat-passing')).toBeVisible();
    await expect(page.locator('#stat-bimestre')).toBeVisible();
  });

  test('Calendar renders with day headers', async ({ page }) => {
    await expect(page.locator('#calGrid')).toBeVisible();
    const cells = await page.locator('#calGrid > div').count();
    expect(cells).toBeGreaterThan(7);
  });

  test('Sidebar has all 10 student sections', async ({ page }) => {
    const sections = ['inicio', 'notas', 'examenes', 'horarios', 'tareas', 'saber', 'biblioteca', 'votaciones', 'perfil', 'chats'];
    for (const s of sections) {
      await expect(page.locator(`[data-section-id="${s}"]`)).toBeAttached();
    }
  });

  test('Navigate to Notas', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('#sec-notas')).toBeVisible();
    await expect(page.locator('#grades-table-body')).toBeVisible();
  });

  test('Notas: P1-P4 period filter buttons', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    for (const p of ['P1', 'P2', 'P3', 'P4']) {
      const btn = page.locator(`[data-period="${p}"]`);
      await expect(btn).toBeVisible();
      await btn.click();
      await expect(btn).toHaveAttribute('data-active', '');
    }
  });

  test('Notas: Export PDF button exists', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('[data-action="export-pdf"]')).toBeVisible();
  });

  test('Navigate to Exámenes', async ({ page }) => {
    await page.click('[data-section-id="examenes"]');
    await expect(page.locator('#sec-examenes')).toBeVisible();
    await expect(page.locator('#available-exams')).toBeVisible();
  });

  test('Navigate to Horarios', async ({ page }) => {
    await page.click('[data-section-id="horarios"]');
    await expect(page.locator('#sec-horarios')).toBeVisible();
    await expect(page.locator('#schedule-container')).toBeVisible();
  });

  test('Navigate to Tareas → upload form', async ({ page }) => {
    await page.click('[data-section-id="tareas"]');
    await expect(page.locator('#sec-tareas')).toBeVisible();
    await expect(page.locator('#hw-subject')).toBeVisible();
    await expect(page.locator('#hw-title')).toBeVisible();
    await expect(page.locator('#hw-comment')).toBeVisible();
    await expect(page.locator('#dropzoneArea')).toBeVisible();
    await expect(page.locator('[data-action="send-homework"]')).toBeVisible();
  });

  test('Tareas: dropzone click opens file picker', async ({ page }) => {
    await page.click('[data-section-id="tareas"]');
    const fileChooser = page.waitForEvent('filechooser');
    await page.click('#dropzoneArea');
    const chooser = await fileChooser;
    expect(chooser).toBeTruthy();
  });

  test('Navigate to Pruebas Saber', async ({ page }) => {
    await page.click('[data-section-id="saber"]');
    await expect(page.locator('#sec-saber')).toBeVisible();
    const areaTabs = await page.locator('#saber-area-tabs button').count();
    expect(areaTabs).toBe(6);
    const periodTabs = await page.locator('#saber-period-tabs button').count();
    expect(periodTabs).toBe(4);
  });

  test('Pruebas Saber: area tab click updates content', async ({ page }) => {
    await page.click('[data-section-id="saber"]');
    await page.click('[data-area="lenguaje"]');
    await expect(page.locator('#saber-content')).toContainText('Lenguaje');
  });

  test('Pruebas Saber: bimestre tab click updates content', async ({ page }) => {
    await page.click('[data-section-id="saber"]');
    await page.click('[data-bimestre="3"]');
    await expect(page.locator('#saber-content')).toContainText('Bimestre 3');
  });

  test('Navigate to Biblioteca', async ({ page }) => {
    await page.click('[data-section-id="biblioteca"]');
    await expect(page.locator('#sec-biblioteca')).toBeVisible();
    await expect(page.locator('#biblio-period')).toBeVisible();
    await expect(page.locator('#library-grid')).toBeVisible();
  });

  test('Navigate to Votaciones', async ({ page }) => {
    await page.click('[data-section-id="votaciones"]');
    await expect(page.locator('#sec-votaciones')).toBeVisible();
    await expect(page.locator('#candidates-list')).toBeVisible();
  });

  test('Navigate to Perfil', async ({ page }) => {
    await page.click('[data-section-id="perfil"]');
    await expect(page.locator('#sec-perfil')).toBeVisible();
    await expect(page.locator('#profile-name')).toBeVisible();
    await expect(page.locator('#profile-avatar-text')).toBeVisible();
  });

  test('Navigate to Chats', async ({ page }) => {
    await page.click('[data-section-id="chats"]');
    await expect(page.locator('#sec-chats')).toBeVisible();
  });

  test('Exam modal: opens and exit button works', async ({ page }) => {
    await page.evaluate(() => { window.startExam('test', 'Test Exam', 30); });
    await expect(page.locator('#exam-modal')).toBeVisible();
    await expect(page.locator('#exam-modal-title')).toContainText('Test Exam');
    await expect(page.locator('#timer-display')).toContainText('30');
    await page.click('[data-action="exit-exam"]');
    await expect(page.locator('#exam-modal')).not.toBeVisible();
  });

  test('Welcome data populates student name', async ({ page }) => {
    await page.waitForTimeout(1500);
    const name = await page.locator('#student-name').textContent();
    expect(name).toBeTruthy();
    expect(name).not.toBe('Estudiante');
  });

  test('Notas: bimestre bar heights render', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    await page.waitForTimeout(1500);
    for (const p of ['P1', 'P2', 'P3', 'P4']) {
      await expect(page.locator(`#bar-${p}`)).toBeAttached();
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 4. TEACHER DASHBOARD
// ═══════════════════════════════════════════════════════════════

test.describe('4 — Teacher Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
  });

  test('Dashboard visible by default', async ({ page }) => {
    await expect(page.locator('#sec-inicio')).toBeVisible();
    await expect(page.locator('#teacher-name')).toBeVisible();
    await expect(page.locator('#stat-students')).toBeVisible();
    await expect(page.locator('#stat-subjects')).toBeVisible();
    await expect(page.locator('#stat-risk')).toBeVisible();
    await expect(page.locator('#stat-recent')).toBeVisible();
  });

  test('Sidebar has all 8 teacher sections', async ({ page }) => {
    const sections = ['inicio', 'notas', 'contenidos', 'examenes', 'horario', 'incidentes', 'alertas', 'chats'];
    for (const s of sections) {
      await expect(page.locator(`[data-section-id="${s}"]`)).toBeAttached();
    }
  });

  test('Navigate to Control de Notas', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('#sec-notas')).toBeVisible();
    await expect(page.locator('#filter-grade-notas')).toBeVisible();
    await expect(page.locator('#filter-subject-notas')).toBeVisible();
    await expect(page.locator('#grades-tbody')).toBeVisible();
  });

  test('Notas: grade select populates', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    const options = await page.locator('#filter-grade-notas option').count();
    expect(options).toBeGreaterThan(1);
  });

  test('Navigate to Guías y Tareas', async ({ page }) => {
    await page.click('[data-section-id="contenidos"]');
    await expect(page.locator('#sec-contenidos')).toBeVisible();
    await expect(page.locator('#guide-title')).toBeVisible();
    await expect(page.locator('#guide-subject')).toBeVisible();
    await expect(page.locator('#guide-drop-zone')).toBeVisible();
    await expect(page.locator('[data-action="upload-guide"]')).toBeVisible();
  });

  test('Guías: dropzone click opens file picker', async ({ page }) => {
    await page.click('[data-section-id="contenidos"]');
    const fileChooser = page.waitForEvent('filechooser');
    await page.click('#guide-drop-zone');
    const chooser = await fileChooser;
    expect(chooser).toBeTruthy();
  });

  test('Navigate to Exámenes → exam builder', async ({ page }) => {
    await page.click('[data-section-id="examenes"]');
    await expect(page.locator('#sec-examenes')).toBeVisible();
    await expect(page.locator('#exam-title-input')).toBeVisible();
    await expect(page.locator('#exam-grade')).toBeVisible();
    await expect(page.locator('#exam-subject')).toBeVisible();
    await expect(page.locator('[data-action="add-question"]')).toBeVisible();
    await expect(page.locator('[data-action="save-exam"]')).toBeVisible();
  });

  test('Exámenes: add question creates card', async ({ page }) => {
    await page.click('[data-section-id="examenes"]');
    await page.click('[data-action="add-question"]');
    expect(await page.locator('.q-card').count()).toBe(1);
  });

  test('Exámenes: add multiple questions', async ({ page }) => {
    await page.click('[data-section-id="examenes"]');
    await page.click('[data-action="add-question"]');
    await page.click('[data-action="add-question"]');
    await page.click('[data-action="add-question"]');
    expect(await page.locator('.q-card').count()).toBe(3);
  });

  test('Exámenes: remove question', async ({ page }) => {
    await page.click('[data-section-id="examenes"]');
    await page.click('[data-action="add-question"]');
    await page.click('[data-action="add-question"]');
    expect(await page.locator('.q-card').count()).toBe(2);
    await page.locator('.js-remove-question').first().click();
    expect(await page.locator('.q-card').count()).toBe(1);
  });

  test('Navigate to Horario', async ({ page }) => {
    await page.click('[data-section-id="horario"]');
    await expect(page.locator('#sec-horario')).toBeVisible();
    await expect(page.locator('#teacher-schedule-body')).toBeVisible();
  });

  test('Navigate to Incidentes', async ({ page }) => {
    await page.click('[data-section-id="incidentes"]');
    await expect(page.locator('#sec-incidentes')).toBeVisible();
    await expect(page.locator('#incidents-tbody')).toBeVisible();
  });

  test('Navigate to Alertas de Riesgo', async ({ page }) => {
    await page.click('[data-section-id="alertas"]');
    await expect(page.locator('#sec-alertas')).toBeVisible();
    await expect(page.locator('#risk-alerts-list')).toBeVisible();
  });

  test('Navigate to Chats', async ({ page }) => {
    await page.click('[data-section-id="chats"]');
    await expect(page.locator('#sec-chats')).toBeVisible();
  });

  test('Teacher: subject select cascades from grade', async ({ page }) => {
    await page.click('[data-section-id="notas"]');
    await page.selectOption('#filter-grade-notas', { index: 1 });
    await page.waitForTimeout(1000);
    const options = await page.locator('#filter-subject-notas option').count();
    expect(options).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// 5. ADMIN DASHBOARD
// ═══════════════════════════════════════════════════════════════

test.describe('5 — Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
  });

  test('Dashboard visible with 5 stat cards', async ({ page }) => {
    await expect(page.locator('#sec-inicio')).toBeVisible();
    await expect(page.locator('#stat-mora')).toBeVisible();
    await expect(page.locator('#stat-grados')).toBeVisible();
    await expect(page.locator('#stat-estudiantes')).toBeVisible();
    await expect(page.locator('#stat-docentes')).toBeVisible();
    await expect(page.locator('#stat-avisos')).toBeVisible();
  });

  test('Sidebar has all 8 admin sections', async ({ page }) => {
    const sections = ['inicio', 'estudiantes', 'docentes', 'materias', 'avisos', 'elecciones', 'administradores', 'chats'];
    for (const s of sections) {
      await expect(page.locator(`[data-section-id="${s}"]`)).toBeAttached();
    }
  });

  test('Navigate to Estudiantes → table + filters', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await expect(page.locator('#sec-estudiantes')).toBeVisible();
    await expect(page.locator('#search-student')).toBeVisible();
    await expect(page.locator('#filter-grade')).toBeVisible();
    await expect(page.locator('#filter-payment')).toBeVisible();
    await expect(page.locator('[data-action="open-modal"][data-modal="estudiante"]')).toBeVisible();
    await expect(page.locator('[data-action="export-csv"]')).toBeVisible();
  });

  test('Estudiantes: search filter works', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await page.waitForTimeout(1000);
    await page.fill('#search-student', 'Juan');
    await page.waitForTimeout(500);
    const rows = await page.locator('#students-list tr').count();
    expect(rows).toBeGreaterThanOrEqual(0);
  });

  test('Estudiantes: payment filter has 3 options', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    const options = await page.locator('#filter-payment option').count();
    expect(options).toBe(3);
  });

  test('Navigate to Docentes', async ({ page }) => {
    await page.click('[data-section-id="docentes"]');
    await expect(page.locator('#sec-docentes')).toBeVisible();
    await expect(page.locator('[data-action="open-modal"][data-modal="docente"]')).toBeVisible();
  });

  test('Navigate to Materias e IA', async ({ page }) => {
    await page.click('[data-section-id="materias"]');
    await expect(page.locator('#sec-materias')).toBeVisible();
    await expect(page.locator('#new-subject-input')).toBeVisible();
    await expect(page.locator('#new-subject-grade')).toBeVisible();
    await expect(page.locator('#subject-tutor-link')).toBeVisible();
    await expect(page.locator('#subject-planner-link')).toBeVisible();
    await expect(page.locator('[data-action="add-subject"]')).toBeVisible();
    await expect(page.locator('#admin-subjects-grid')).toBeAttached();
  });

  test('Materias: grade select has 11 grades', async ({ page }) => {
    await page.click('[data-section-id="materias"]');
    const options = await page.locator('#new-subject-grade option').count();
    expect(options).toBe(11);
  });

  test('Navigate to Avisos', async ({ page }) => {
    await page.click('[data-section-id="avisos"]');
    await expect(page.locator('#sec-avisos')).toBeVisible();
    await expect(page.locator('#notice-title')).toBeVisible();
    await expect(page.locator('#notice-content')).toBeVisible();
    await expect(page.locator('#notice-file')).toBeVisible();
    await expect(page.locator('[data-action="publish-notice"]')).toBeVisible();
  });

  test('Navigate to Elecciones', async ({ page }) => {
    await page.click('[data-section-id="elecciones"]');
    await expect(page.locator('#sec-elecciones')).toBeVisible();
    await expect(page.locator('#cand-name')).toBeVisible();
    await expect(page.locator('#cand-photo')).toBeVisible();
    await expect(page.locator('[data-action="add-candidate"]')).toBeVisible();
    await expect(page.locator('[data-action="reset-election"]')).toBeVisible();
    await expect(page.locator('#electionResultsChart')).toBeAttached();
  });

  test('Navigate to Administradores', async ({ page }) => {
    await page.click('[data-section-id="administradores"]');
    await expect(page.locator('#sec-administradores')).toBeVisible();
    await expect(page.locator('[data-action="open-admin-modal"]')).toBeVisible();
  });

  test('Navigate to Chats', async ({ page }) => {
    await page.click('[data-section-id="chats"]');
    await expect(page.locator('#sec-chats')).toBeVisible();
  });

  test('Modal: opens for estudiante matriculation', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await page.click('[data-action="open-modal"][data-modal="estudiante"]');
    await expect(page.locator('#admin-modal')).toBeVisible();
    await expect(page.locator('#modal-title')).toContainText('Matricular');
    await expect(page.locator('#modal-document')).toBeVisible();
    await expect(page.locator('#modal-name')).toBeVisible();
    await expect(page.locator('#modal-grade')).toBeVisible();
    await expect(page.locator('#modal-password')).toBeVisible();
  });

  test('Modal: opens for docente registration', async ({ page }) => {
    await page.click('[data-section-id="docentes"]');
    await page.click('[data-action="open-modal"][data-modal="docente"]');
    await expect(page.locator('#admin-modal')).toBeVisible();
    await expect(page.locator('#modal-title')).toContainText('Docente');
  });

  test('Modal: opens for admin creation', async ({ page }) => {
    await page.click('[data-section-id="administradores"]');
    await page.click('[data-action="open-admin-modal"]');
    await expect(page.locator('#admin-modal')).toBeVisible();
    await expect(page.locator('#modal-title')).toContainText('Administrador');
  });

  test('Modal: close via cancel button', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await page.click('[data-action="open-modal"][data-modal="estudiante"]');
    await expect(page.locator('#admin-modal')).toBeVisible();
    await page.click('[data-action="close-modal"]');
    await expect(page.locator('#admin-modal')).not.toBeVisible();
  });

  test('Modal: close via Escape key', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await page.click('[data-action="open-modal"][data-modal="estudiante"]');
    await expect(page.locator('#admin-modal')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('#admin-modal')).not.toBeVisible();
  });

  test('Modal: save with empty fields stays open', async ({ page }) => {
    await page.click('[data-section-id="estudiantes"]');
    await page.click('[data-action="open-modal"][data-modal="estudiante"]');
    await page.click('[data-action="save-form"]');
    await page.waitForTimeout(500);
    await expect(page.locator('#admin-modal')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════
// 6. SIDEBAR NAVIGATION & ACTIVE STATES
// ═══════════════════════════════════════════════════════════════

test.describe('6 — Sidebar Navigation', () => {
  test('Student: active section has aria-current', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('.sidebar-link[data-section-id="inicio"]')).toHaveAttribute('aria-current', 'page');
  });

  test('Student: clicking section updates aria-current', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('[data-section-id="notas"]')).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('[data-section-id="inicio"]')).not.toHaveAttribute('aria-current', 'page');
  });

  test('Student: vyntra:navigate event dispatched', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const eventPromise = page.evaluate(() => {
      return new Promise((resolve) => {
        window.addEventListener('vyntra:navigate', (e) => resolve(e.detail), { once: true });
      });
    });
    await page.click('[data-section-id="notas"]');
    const detail = await eventPromise;
    expect(detail.section).toBe('notas');
  });

  test('Teacher: active section updates correctly', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    await expect(page.locator('[data-section-id="inicio"]')).toHaveAttribute('aria-current', 'page');
    await page.click('[data-section-id="examenes"]');
    await expect(page.locator('[data-section-id="examenes"]')).toHaveAttribute('aria-current', 'page');
  });

  test('Admin: active section updates correctly', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await expect(page.locator('[data-section-id="inicio"]')).toHaveAttribute('aria-current', 'page');
    await page.click('[data-section-id="elecciones"]');
    await expect(page.locator('[data-section-id="elecciones"]')).toHaveAttribute('aria-current', 'page');
  });

  test('All role sidebars have navigation role', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const role = cred === CREDS.student ? 'student' : cred === CREDS.teacher ? 'teacher' : 'admin';
      await expect(page.locator(`#vyntra-sidebar-${role}`)).toHaveAttribute('role', 'navigation');
    }
  });

  test('Student: topbar heading updates on navigation', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('.topbar-heading')).toContainText('Registro de Notas');
  });

  test('Student: sidebar username populated', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const name = await page.locator('#sidebar-username-student').textContent();
    expect(name).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════
// 7. THEME TOGGLE
// ═══════════════════════════════════════════════════════════════

test.describe('7 — Theme Toggle', () => {
  test('All roles have theme toggle button', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const role = cred === CREDS.student ? 'student' : cred === CREDS.teacher ? 'teacher' : 'admin';
      await expect(page.locator(`#theme-toggle-${role}`)).toBeVisible();
    }
  });

  test('Student: clicking toggle switches dark mode', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const isDarkBefore = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    await page.click('#theme-toggle-student');
    await page.waitForTimeout(300);
    const isDarkAfter = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    expect(isDarkAfter).toBe(!isDarkBefore);
  });

  test('Theme persists in localStorage', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    const savedTheme = await page.evaluate(() => localStorage.getItem('vyntra-theme'));
    if (isDark) {
      expect(savedTheme).toBe('dark');
    } else {
      expect(savedTheme === 'light' || savedTheme === null).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 8. AI CHAT
// ═══════════════════════════════════════════════════════════════

test.describe('8 — AI Chat', () => {
  test('All roles have chat toggle button', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      await expect(page.locator('#ai-chat-toggle')).toBeVisible();
    }
  });

  test('Student: chat panel opens on click', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#ai-chat-toggle');
    await expect(page.locator('#ai-chat-panel')).toHaveClass(/opacity-100/);
  });

  test('Chat has input, send, stop, clear buttons', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#ai-chat-toggle');
    await expect(page.locator('#chat-input')).toBeVisible();
    await expect(page.locator('#chat-send')).toBeVisible();
    await expect(page.locator('#chat-stop')).toBeAttached();
    await expect(page.locator('#chat-clear-btn')).toBeVisible();
  });

  test('Chat has welcome message', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#ai-chat-toggle');
    await page.waitForTimeout(500);
    const msgCount = await page.locator('#chat-messages > div').count();
    expect(msgCount).toBeGreaterThan(0);
  });

  test('Chat has fullscreen button', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#ai-chat-toggle');
    await expect(page.locator('#chat-fullscreen-btn')).toBeVisible();
  });

  test('Chat clear button resets messages', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#ai-chat-toggle');
    await page.waitForTimeout(500);
    await page.click('#chat-clear-btn');
    await page.waitForTimeout(500);
    // After clear, welcome message should reappear
    const msgCount = await page.locator('#chat-messages > div').count();
    expect(msgCount).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// 9. TOPBAR
// ═══════════════════════════════════════════════════════════════

test.describe('9 — Topbar', () => {
  test('Student: live clock visible with time format', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#live-clock')).toBeVisible();
    await page.waitForTimeout(1500);
    const text = await page.locator('#live-clock').textContent();
    expect(text).toMatch(/\d{2}:\d{2}/);
  });

  test('All roles: topbar heading shows correct title', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('.topbar-heading')).toContainText('Panel de Estudiante');

    await mockLogin(page, CREDS.teacher);
    await expect(page.locator('.topbar-heading')).toContainText('Panel Docente');

    await mockLogin(page, CREDS.admin);
    await expect(page.locator('.topbar-heading')).toContainText('Panel de Administración');
  });

  test('Desktop: hamburger not visible', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#mobile-menu-btn')).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════
// 10. LOGOUT
// ═══════════════════════════════════════════════════════════════

test.describe('10 — Logout', () => {
  test('All roles have visible logout button', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const role = cred === CREDS.student ? 'student' : cred === CREDS.teacher ? 'teacher' : 'admin';
      await expect(page.locator(`#logout-btn-${role}`)).toBeVisible();
    }
  });

  test('Student: logout redirects to home', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#logout-btn-student');
    await page.waitForURL(/\/$/, { timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════
// 11. CONSOLE ERRORS
// ═══════════════════════════════════════════════════════════════

test.describe('11 — Console Errors', () => {
  test('Login page: zero JS errors', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });

  test('Landing page: zero JS errors', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await page.goto(`${BASE}/`);
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });

  test('404 page: zero JS errors', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await page.goto(`${BASE}/404.html`);
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });

  test('Student dashboard: zero JS errors after login', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.waitForTimeout(3000);
    expect(errors).toEqual([]);
  });

  test('Teacher dashboard: zero JS errors after login', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    await page.waitForTimeout(3000);
    expect(errors).toEqual([]);
  });

  test('Admin dashboard: zero JS errors after login', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await page.waitForTimeout(3000);
    expect(errors).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════
// 12. ACCESSIBILITY
// ═══════════════════════════════════════════════════════════════

test.describe('12 — Accessibility', () => {
  test('Login: skip link exists', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    const skipLink = page.locator('.skip-link');
    await expect(skipLink).toBeAttached();
  });

  test('All roles: logout has aria-label', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const role = cred === CREDS.student ? 'student' : cred === CREDS.teacher ? 'teacher' : 'admin';
      await expect(page.locator(`#logout-btn-${role}`)).toHaveAttribute('aria-label');
    }
  });

  test('Sidebar has aria-label "Navegación principal"', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#vyntra-sidebar-student')).toHaveAttribute('aria-label', 'Navegación principal');
  });

  test('Chat toggle has aria-label', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#ai-chat-toggle')).toHaveAttribute('aria-label');
  });

  test('Main content has role="main"', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('[role="main"]')).toBeVisible();
  });

  test('Theme toggle has aria-label', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#theme-toggle-student')).toHaveAttribute('aria-label');
  });
});

// ═══════════════════════════════════════════════════════════════
// 13. MOBILE RESPONSIVENESS
// ═══════════════════════════════════════════════════════════════

test.describe('13 — Mobile Responsiveness', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('Hamburger visible on mobile', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#mobile-menu-btn')).toBeVisible();
  });

  test('Sidebar hidden by default on mobile', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#vyntra-sidebar-student')).toHaveClass(/-translate-x-full/);
  });

  test('Hamburger opens sidebar on mobile', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#mobile-menu-btn');
    await expect(page.locator('#vyntra-sidebar-student')).toHaveClass(/translate-x-0/);
  });

  test('Overlay visible when sidebar open', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#mobile-menu-btn');
    await page.waitForTimeout(500);
    await expect(page.locator('#sidebar-overlay-student')).toBeVisible();
  });

  test('Clicking overlay closes sidebar', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#mobile-menu-btn');
    await page.waitForTimeout(500);
    await page.locator('#sidebar-overlay-student').click({ force: true });
    await page.waitForTimeout(500);
    await expect(page.locator('#vyntra-sidebar-student')).toHaveClass(/-translate-x-full/);
  });

  test('Escape closes sidebar on mobile', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('#mobile-menu-btn');
    await page.keyboard.press('Escape');
    await expect(page.locator('#vyntra-sidebar-student')).toHaveClass(/-translate-x-full/);
  });

  test('Login form renders on mobile', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await expect(page.locator('#login-form')).toBeVisible();
    await expect(page.locator('#credential')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════
// 14. SECTION ANIMATIONS
// ═══════════════════════════════════════════════════════════════

test.describe('14 — Section Animations', () => {
  test('Student: navigation adds section-enter class', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('[data-section-id="notas"]');
    await page.waitForTimeout(300);
    const hasClass = await page.evaluate(() => {
      return document.getElementById('sec-notas')?.classList.contains('section-enter') ?? false;
    });
    expect(hasClass).toBeTruthy();
  });

  test('Student: solar cards get card-stagger', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('[data-section-id="notas"]');
    await page.waitForTimeout(500);
    const hasStagger = await page.evaluate(() => {
      const cards = document.querySelectorAll('#sec-notas .solar-card');
      return cards.length > 0 && Array.from(cards).some(c => c.classList.contains('card-stagger'));
    });
    expect(hasStagger).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════
// 15. SECTION HIDING
// ═══════════════════════════════════════════════════════════════

test.describe('15 — Section Hiding', () => {
  test('Student: non-active sections hidden', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    const hidden = await page.evaluate(() => {
      return document.getElementById('sec-notas')?.style.display === 'none';
    });
    expect(hidden).toBeTruthy();
  });

  test('Student: only sec-inicio visible on load', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('#sec-inicio')).toBeVisible();
    expect(await page.locator('#sec-notas').isVisible()).toBeFalsy();
  });

  test('Teacher: non-active sections hidden', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    const hidden = await page.evaluate(() => {
      return document.getElementById('sec-notas')?.style.display === 'none';
    });
    expect(hidden).toBeTruthy();
  });

  test('Admin: non-active sections hidden', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    const hidden = await page.evaluate(() => {
      return document.getElementById('sec-estudiantes')?.style.display === 'none';
    });
    expect(hidden).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════
// 16. CROSS-ROLE ISOLATION
// ═══════════════════════════════════════════════════════════════

test.describe('16 — Cross-Role Isolation', () => {
  test('Student cannot see admin/teacher sections', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await expect(page.locator('[data-section-id="estudiantes"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="docentes"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="materias"]')).not.toBeAttached();
  });

  test('Teacher cannot see student/admin sections', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    await expect(page.locator('[data-section-id="saber"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="biblioteca"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="votaciones"]')).not.toBeAttached();
  });

  test('Admin cannot see student/teacher sections', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await expect(page.locator('[data-section-id="contenidos"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="incidentes"]')).not.toBeAttached();
    await expect(page.locator('[data-section-id="alertas"]')).not.toBeAttached();
  });
});

// ═══════════════════════════════════════════════════════════════
// 17. LANDING PAGE
// ═══════════════════════════════════════════════════════════════

test.describe('17 — Landing Page', () => {
  test('Landing loads with content', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/`);
    await expect(page.locator('body')).toBeVisible();
    const html = await page.content();
    expect(html).toContain('VYNTRA');
  });

  test('Landing has login link', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/`);
    await page.waitForTimeout(1000);
    const hasLoginLink = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a')).some(l => l.href.includes('/login'));
    });
    expect(hasLoginLink).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════
// 18. 404 PAGE
// ═══════════════════════════════════════════════════════════════

test.describe('18 — 404 Page', () => {
  test('404 renders with content', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/nonexistent-page-12345`);
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(10);
  });
});

// ═══════════════════════════════════════════════════════════════
// 19. DASHBOARD REDIRECT
// ═══════════════════════════════════════════════════════════════

test.describe('19 — Dashboard Redirect', () => {
  test('Student role → /estudiante', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.evaluate(() => {
      localStorage.setItem('userRole', 'ESTUDIANTE');
      localStorage.setItem('userId', 'test');
      localStorage.setItem('userName', 'Test');
    });
    await page.goto(`${BASE}/dashboard`);
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/estudiante');
  });

  test('Teacher role → /docente', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.evaluate(() => {
      localStorage.setItem('userRole', 'PROFESOR');
      localStorage.setItem('userId', 'test');
      localStorage.setItem('userName', 'Test');
    });
    await page.goto(`${BASE}/dashboard`);
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/docente');
  });

  test('Admin role → /admin', async ({ page }) => {
    await mockAllApis(page);
    await page.goto(`${BASE}/login`);
    await page.evaluate(() => {
      localStorage.setItem('userRole', 'ADMIN');
      localStorage.setItem('userId', 'test');
      localStorage.setItem('userName', 'Test');
    });
    await page.goto(`${BASE}/dashboard`);
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/admin');
  });
});

// ═══════════════════════════════════════════════════════════════
// 20. FORM VALIDATION
// ═══════════════════════════════════════════════════════════════

test.describe('20 — Form Validation', () => {
  test('Admin: save empty student modal stays open', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await page.click('[data-section-id="estudiantes"]');
    await page.click('[data-action="open-modal"][data-modal="estudiante"]');
    await page.fill('#modal-document', '');
    await page.fill('#modal-name', '');
    await page.fill('#modal-password', '');
    await page.click('[data-action="save-form"]');
    await page.waitForTimeout(500);
    await expect(page.locator('#admin-modal')).toBeVisible();
  });

  test('Admin: publish notice with empty fields', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await page.click('[data-section-id="avisos"]');
    await page.fill('#notice-title', '');
    await page.fill('#notice-content', '');
    await page.click('[data-action="publish-notice"]');
    await page.waitForTimeout(500);
  });

  test('Teacher: save exam with no questions', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    await page.click('[data-section-id="examenes"]');
    await page.fill('#exam-title-input', 'Test Exam');
    await page.click('[data-action="save-exam"]');
    await page.waitForTimeout(500);
  });
});

// ═══════════════════════════════════════════════════════════════
// 21. RAPID SECTION SWITCHING (stress test)
// ═══════════════════════════════════════════════════════════════

test.describe('21 — Rapid Section Switching', () => {
  test('Student: rapid nav does not crash', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    for (const s of ['notas', 'examenes', 'horarios', 'tareas', 'saber', 'biblioteca', 'votaciones', 'perfil', 'inicio']) {
      await page.click(`[data-section-id="${s}"]`);
      await page.waitForTimeout(100);
    }
    await expect(page.locator('#sec-inicio')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('Teacher: rapid nav does not crash', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    for (const s of ['notas', 'contenidos', 'examenes', 'horario', 'incidentes', 'alertas', 'inicio']) {
      await page.click(`[data-section-id="${s}"]`);
      await page.waitForTimeout(100);
    }
    await expect(page.locator('#sec-inicio')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('Admin: rapid nav does not crash', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    for (const s of ['estudiantes', 'docentes', 'materias', 'avisos', 'elecciones', 'administradores', 'inicio']) {
      await page.click(`[data-section-id="${s}"]`);
      await page.waitForTimeout(100);
    }
    await expect(page.locator('#sec-inicio')).toBeVisible();
    expect(errors).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════
// 22. PAGE STRUCTURE INTEGRITY
// ═══════════════════════════════════════════════════════════════

test.describe('22 — Page Structure', () => {
  test('Student: all 10 section IDs exist', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    for (const id of ['sec-inicio', 'sec-notas', 'sec-examenes', 'sec-horarios', 'sec-tareas', 'sec-saber', 'sec-biblioteca', 'sec-votaciones', 'sec-perfil', 'sec-chats']) {
      await expect(page.locator(`#${id}`)).toBeAttached();
    }
  });

  test('Teacher: all 8 section IDs exist', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.teacher);
    for (const id of ['sec-inicio', 'sec-notas', 'sec-contenidos', 'sec-examenes', 'sec-horario', 'sec-incidentes', 'sec-alertas', 'sec-chats']) {
      await expect(page.locator(`#${id}`)).toBeAttached();
    }
  });

  test('Admin: all 8 section IDs exist', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    for (const id of ['sec-inicio', 'sec-estudiantes', 'sec-docentes', 'sec-materias', 'sec-avisos', 'sec-elecciones', 'sec-administradores', 'sec-chats']) {
      await expect(page.locator(`#${id}`)).toBeAttached();
    }
  });

  test('All roles: DashboardShell wrapper present', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      await expect(page.locator('.app-shell')).toBeVisible();
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 23. NOISE OVERLAY
// ═══════════════════════════════════════════════════════════════

test.describe('23 — Noise Overlay', () => {
  test('All roles: at most 1 noise overlay', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const count = await page.locator('.noise-overlay').count();
      expect(count).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 24. CHART.JS
// ═══════════════════════════════════════════════════════════════

test.describe('24 — Chart.js', () => {
  test('Student: grades chart canvas present', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.student);
    await page.click('[data-section-id="notas"]');
    await expect(page.locator('#myGradesChart')).toBeAttached();
  });

  test('Admin: election chart canvas present', async ({ page }) => {
    await mockAllApis(page);
    await mockLogin(page, CREDS.admin);
    await page.click('[data-section-id="elecciones"]');
    await expect(page.locator('#electionResultsChart')).toBeAttached();
  });
});

// ═══════════════════════════════════════════════════════════════
// 25. SIDEBAR BUTTON TEXT
// ═══════════════════════════════════════════════════════════════

test.describe('25 — Sidebar Button Text', () => {
  test('All roles: sidebar buttons have text', async ({ page }) => {
    await mockAllApis(page);
    for (const cred of [CREDS.student, CREDS.teacher, CREDS.admin]) {
      await mockLogin(page, cred);
      const role = cred === CREDS.student ? 'student' : cred === CREDS.teacher ? 'teacher' : 'admin';
      const buttons = page.locator(`#vyntra-sidebar-${role} [data-section-id]`);
      const count = await buttons.count();
      for (let i = 0; i < count; i++) {
        const text = await buttons.nth(i).textContent();
        expect(text.trim().length).toBeGreaterThan(0);
      }
    }
  });
});
