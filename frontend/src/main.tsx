import React from 'react';
import ReactDOM from 'react-dom/client';

function App() {
  return (
    <main style={{ fontFamily: 'system-ui', maxWidth: 720, margin: '4rem auto', padding: '0 1rem' }}>
      <h1>Manuable · Cotizador de envíos</h1>
      <p>La plataforma está iniciada. En el siguiente paso construiremos el formulario de cotización.</p>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
