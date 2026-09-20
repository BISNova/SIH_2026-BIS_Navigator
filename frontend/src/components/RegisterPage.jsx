import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { AuthAPIError } from '../auth';

// Admin is deliberately not an option here - server-side seeded only,
// per backend confirmation. Only these three are allowed from the
// frontend.
const ROLES = [
  { value: 'general', label: 'General User' },
  { value: 'msme', label: 'MSME / Manufacturer' },
  { value: 'lab', label: 'Testing Lab' },
];

export default function RegisterPage({ onGoToLogin, onBack }) {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('general');
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);

    try {
      await register({ name, email, password, role });

      // Registration never auto-logs in (see AuthContext) - so the
      // message here is the ONLY place a lab user finds out they're
      // pending, before they even try to log in.
      setSuccessMessage(
        role === 'lab'
          ? "Registration submitted. Your lab account needs approval before you can log in - please check back later."
          : 'Account created. You can log in now.'
      );
    } catch (err) {
      if (err instanceof AuthAPIError && err.status === 409) {
        setError('An account with this email already exists. Try logging in instead.');
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

        <h1 className="auth-title">Create your account</h1>

        {error && <div className="auth-error">{error}</div>}
        {successMessage && (
          <div className="auth-success">
            {successMessage}
            <div>
              <button type="button" className="auth-link-btn" onClick={onGoToLogin}>
                Go to login →
              </button>
            </div>
          </div>
        )}

        {!successMessage && (
          <>
            <label className="auth-label">
              Name
              <input
                type="text"
                className="auth-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>

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

            <label className="auth-label password-field">
              Password
              <input
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((prev) => !prev)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </label>

            <label className="auth-label">
              I am a...
              <select
                className="auth-input"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>

            {role === 'lab' && (
              <p className="auth-hint">
                Lab accounts require manual approval before you can log in.
              </p>
            )}

            <button type="submit" className="auth-submit-btn" disabled={isSubmitting}>
              {isSubmitting ? 'Creating account…' : 'Register'}
            </button>

            <p className="auth-switch-line">
              Already have an account?{' '}
              <button type="button" className="auth-link-btn" onClick={onGoToLogin}>
                Log in
              </button>
            </p>
          </>
        )}
      </form>
    </div>
  );
}