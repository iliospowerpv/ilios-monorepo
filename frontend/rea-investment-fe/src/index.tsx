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
// that occur when layout changes happen faster than the observer can process
const resizeObserverErr = (e: ErrorEvent) => {
  if (e.message === 'ResizeObserver loop completed with undelivered notifications.') {
    e.stopImmediatePropagation();
  }
};
window.addEventListener('error', resizeObserverErr);

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<App />);
