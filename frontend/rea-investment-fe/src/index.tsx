import React from 'react';
import ReactDOM from 'react-dom/client';
import { LicenseManager } from 'ag-grid-enterprise';
import './index.css';
import './styles/focus-highlight.css';
import App from './App';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

// Suppress ResizeObserver loop errors - these are benign browser notifications
// that occur when layout changes happen faster than the observer can process.
// This requires multiple handlers to catch it before React's error overlay.
const resizeObserverErrMsg = 'ResizeObserver loop completed with undelivered notifications.';

// Handler for ErrorEvent
const resizeObserverErr = (e: ErrorEvent) => {
  if (e.message === resizeObserverErrMsg) {
    e.stopImmediatePropagation();
    e.preventDefault();
    return false;
  }
};

// Handler for unhandled errors (catches before React overlay)
window.onerror = function (message) {
  if (message === resizeObserverErrMsg) {
    return true; // Prevents the error from propagating
  }
  return false;
};

window.addEventListener('error', resizeObserverErr, true); // Use capture phase

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<App />);
