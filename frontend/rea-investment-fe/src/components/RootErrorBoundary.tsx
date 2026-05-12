import React from 'react';

interface RootErrorBoundaryProps {
  children: React.ReactNode;
}

interface RootErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class RootErrorBoundary extends React.Component<RootErrorBoundaryProps, RootErrorBoundaryState> {
  constructor(props: RootErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): RootErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[RootErrorBoundary] Render error:', error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div
        role="alert"
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          background: '#fafafa',
          color: '#202020'
        }}
      >
        <div
          style={{
            maxWidth: '480px',
            textAlign: 'center',
            padding: '32px',
            border: '1px solid #e0e0e0',
            borderRadius: '8px',
            background: '#fff',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
          }}
        >
          <h1 style={{ fontSize: '20px', margin: '0 0 12px', fontWeight: 600 }}>Something went wrong.</h1>
          <p style={{ margin: '0 0 24px', color: '#555', lineHeight: 1.5 }}>
            The application hit an unexpected error and could not continue rendering. Please refresh the page. If the
            problem keeps happening, contact your iliOS administrator with the time it occurred.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              fontWeight: 500,
              color: '#fff',
              background: '#1976d2',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Refresh page
          </button>
        </div>
      </div>
    );
  }
}

export default RootErrorBoundary;
