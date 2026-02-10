import React, { useEffect, useState } from 'react';

const App: React.FC = () => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('http://localhost:8000/items')
      .then(res => res.arrayBuffer())
      .then(buffer => {
        // Parse Arrow IPC (use arrow-js or similar lib in prod)
        console.log('Arrow data received:', buffer);
        setData(buffer);
      });
  }, []);

  return (
    <div>
      <h1>FARM Stack Boilerplate</h1>
      <p>Data from backend (Arrow format): {data ? 'Loaded' : 'Loading...'}</p>
    </div>
  );
};

export default App;