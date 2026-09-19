import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { AuthAPIError } from '../auth';

export default function LoginPage({ onLoginSuccess, onGoToRegister, onBack }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login(email, password);
      onLoginSuccess(user);
    } catch (err) {
      if (err instanceof AuthAPIError && err.status === 401) {
        setError('Incorrect email or password.');
      } else if (err instanceof AuthAPIError && err.status === 403) {
        // Covers the "pending" lab-account case, and any other
        // authenticated-but-not-allowed-in case the backend adds later.
        setError(
          err.detail && err.detail.toLowerCase().includes('pending')
            ? "Your account is pending approval and can't log in yet. Please check back later."
            : (err.detail || 'Access denied for this account.')
        );
      } else if (err instanceof AuthAPIError) {
        setError(err.message);
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <button type="button" className="auth-back-link" onClick={onBack}>
          ← Back
        </button>

        <h1 className="auth-title">Log in to BISNova</h1>
        <p className="auth-subtitle">
          Chat works without an account - log in for admin and account features.
        </p>

        {error && <div className="auth-error">{error}</div>}

        <label className="auth-label">
          Email
          <input
            type="email"
            className="auth-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>

        <label className="auth-label">
          Password
          <input
            type="password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        <button type="submit" className="auth-submit-btn" disabled={isSubmitting}>
          {isSubmitting ? 'Logging in…' : 'Log In'}
        </button>

        <p className="auth-switch-line">
          Don't have an account?{' '}
          <button type="button" className="auth-link-btn" onClick={onGoToRegister}>
            Register
          </button>
        </p>
      </form>
    </div>
  );
}