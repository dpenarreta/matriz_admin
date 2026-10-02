import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../../components/common/Button/Button";
import { useAuth } from "../../hooks/useAuth";
import "./Login.css";

export function Login() {
  const { login, isLoading, error } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ identifier: "", password: "" });

  function handleChange(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    try {
      const me = await login(form);
      navigate(me.must_change_password ? "/change-password-required" : "/");
    } catch {
      // El mensaje de error ya se expone vía useAuth().error
    }
  }

  return (
    <div className="login-screen">
      <aside className="login-aside">
        <div className="login-brand">
          <span className="login-glyph">MA</span> Matriz Administrativa de Obligaciones
        </div>
        <div className="login-pitch">
          <h1>Un solo panel para cada obligación, cada vencimiento y cada evidencia.</h1>
          <p>
            Centraliza obligaciones regulatorias, contractuales e internas por área y entidad de control. Asigna
            responsables, controla fechas límite, conserva el PDF de respaldo y automatiza los recordatorios por correo.
          </p>
        </div>
        <div className="login-foot">Laarcourier · Laar Seguridad · Virtual Create</div>
      </aside>
      <main className="login-main">
        <form onSubmit={handleSubmit} className="login-card">
          <h2>Acceso al sistema</h2>
          <p className="login-sub">Ingrese con su usuario corporativo. Después podrá elegir la empresa.</p>
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="mb-3">
            <label className="form-label" htmlFor="identifier">
              Usuario o correo
            </label>
            <input
              id="identifier"
              name="identifier"
              className="form-control"
              autoComplete="username"
              value={form.identifier}
              onChange={handleChange}
              required
            />
          </div>
          <div className="mb-3">
            <label className="form-label" htmlFor="password">
              Contraseña
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="form-control"
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>
          <Button type="submit" isLoading={isLoading}>
            Ingresar
          </Button>
          <div className="mt-3">
            <Link to="/forgot-password">¿Olvidó su contraseña?</Link>
          </div>
        </form>
      </main>
    </div>
  );
}
