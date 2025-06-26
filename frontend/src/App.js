import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import logo from './assets/logo.png'; 
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Tercih botuna hoşgeldin. Üniversiteler hakkında merak ettiklerini sorabilirsin...' }
  ]);
  const [input, setInput] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isBotTyping, setIsBotTyping] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  const chatEndRef = useRef(null);

  useEffect(() => {
    document.documentElement.className = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  const senderId = (() => {
    const stored = localStorage.getItem('sender_id');
    if (stored) return stored;
    const newId = uuidv4();
    localStorage.setItem('sender_id', newId);
    return newId;
  })();

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsBotTyping(true);
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, sender_id: senderId })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { sender: 'bot', text: data.response }]);
      if (data.pdf) setPdfFile(data.pdf);
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'bot', text: '❗ Hata oluştu.' }]);
    }
    setIsBotTyping(false);
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleDownload = () => {
    if (!pdfFile) return;
    setIsDownloading(true);
    const url = `http://localhost:8000/pdfs/${pdfFile}`;
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => {
      setIsDownloading(false);
    }, 1500);
  };

  return (
    <div className="app-container">
      <div className="theme-toggle-button" onClick={toggleTheme}>
        {theme === 'light' ? '🌙' : '☀️'}
      </div>
      <div className="center-content">
        <img src={logo} alt="logo" className="logo" />
        <h1>TERCİH BOTU</h1>
      </div>

      <div className="messages-overlay">
        {messages.map((msg, i) => (
          <div key={i} className={`bubble ${msg.sender}`}>
            {msg.text.split('\n').map((line, index) => (
              <div key={index}>{line}</div>
            ))}
            {msg.sender === 'bot' && pdfFile && i === messages.length - 1 && (
              <div style={{ marginTop: '12px', textAlign: 'left' }}>
                <button className="pdf-button" onClick={handleDownload} disabled={isDownloading}>
                  {isDownloading ? "⏳ İndiriliyor..." : "📄 PDF İndir"}
                </button>
              </div>
            )}
          </div>
        ))}
        {isBotTyping && (
          <div className="bubble bot">
            <div className="typing-indicator">
              <img src={logo} alt="logo" className="typing-logo" />
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="input-area-overlay">
        <input
          type="text"
          value={input}
          placeholder="Tercih sorunuzu yazın..."
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage}>
          <span style={{ fontSize: '1.3em' }}>➔</span>
        </button>
      </div>
    </div>
  );
}

export default App;