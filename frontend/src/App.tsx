import React, { useEffect, useState } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000';

const App: React.FC = () => {
  const [byteLength, setByteLength] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/items`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`);
        }
        return res.arrayBuffer();
      })
      .then((buffer) => {
        // Arrow IPC stream bytes; parse with apache-arrow in a real app.
        console.log('Arrow data received:', buffer);
        setByteLength(buffer.byteLength);
      })
      .catch((err: unknown) => setError(String(err)));
  }, []);

  return (
    <div>
      <h1>FARM Stack Boilerplate</h1>
      {error ? (
        <p>Error loading data: {error}</p>
      ) : (
        <p>
          Data from backend (Arrow format):{' '}
          {byteLength === null ? 'Loading...' : `Loaded ${byteLength} bytes`}
        </p>
      )}
    </div>
  );
};

export default App;
