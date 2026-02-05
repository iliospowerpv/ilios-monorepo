import React from 'react';
import ReactDOM from 'react-dom/client';
import { LicenseManager } from 'ag-grid-enterprise';
import './index.css';
import './styles/focus-highlight.css';
import App from './App';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

// Patch ResizeObserver to suppress benign "loop completed" errors.
// This error occurs when layout changes happen faster than the observer can process,
// which is normal behavior with AG Grid and other complex components.
// We patch at the source to prevent the error from reaching React's error overlay.
const OriginalResizeObserver = window.ResizeObserver;
window.ResizeObserver = class ResizeObserver extends OriginalResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    super((entries, observer) => {
      // Use requestAnimationFrame to batch updates and prevent the loop error
      window.requestAnimationFrame(() => {
        callback(entries, observer);
      });
    });
  }
};

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<App />);
