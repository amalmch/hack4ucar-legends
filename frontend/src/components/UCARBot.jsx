import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, Send, User, Sparkles } from 'lucide-react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';

export default function UCARBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'bot', text: "Bonjour ! Je suis l'Assistant IA d'UCAR. Comment puis-je vous aider ?" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const { user } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  // Show for ALL authenticated users
  if (!user) return null;

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const res = await api.post('/api/ai/chat', { message: userMsg });
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: res.data.response 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: "Désolé, je n'ai pas pu joindre le serveur. Veuillez réessayer." 
      }]);
    }
    setLoading(false);
  };

  return (
    <>
      {/* Bot Toggle Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 p-4 rounded-full shadow-2xl transition-all duration-300 z-50 ${
          isOpen ? 'bg-slate-800 text-white rotate-90 scale-90' : 'bg-ucar-600 text-white hover:bg-ucar-700 hover:scale-110 hover:shadow-ucar-600/50'
        }`}
      >
        {isOpen ? <X size={24} /> : <Bot size={28} />}
      </button>

      {/* Chat Window */}
      <div 
        className={`fixed bottom-24 right-6 w-[400px] h-[600px] max-h-[80vh] max-w-[90vw] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden transition-all duration-500 origin-bottom-right z-40 ${
          isOpen ? 'scale-100 opacity-100 translate-y-0' : 'scale-50 opacity-0 translate-y-10 pointer-events-none'
        }`}
      >
        {/* Header */}
        <div className="bg-accent-gradient p-4 text-white flex items-center justify-between shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center">
              <Bot size={24} className="text-white" />
            </div>
            <div>
              <h3 className="font-bold font-display leading-tight flex items-center gap-1">
                UCAR AI Assistant <Sparkles size={14} className="text-amber-300" />
              </h3>
              <p className="text-xs text-ucar-100 font-medium">Propulsé par LLaMA 3 & Groq</p>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 p-4 overflow-y-auto bg-slate-50 flex flex-col gap-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 max-w-[90%] ${msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm mt-1 ${
                msg.sender === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-ucar-100 text-ucar-600'
              }`}>
                {msg.sender === 'user' ? <User size={16} /> : <Bot size={18} />}
              </div>
              <div className={`p-3 rounded-2xl shadow-sm text-sm leading-relaxed overflow-hidden ${
                msg.sender === 'user' 
                  ? 'bg-ucar-600 text-white rounded-tr-none' 
                  : 'bg-white text-slate-700 border border-slate-100 rounded-tl-none prose prose-sm prose-slate prose-p:my-1 prose-ul:my-1'
              }`}>
                {msg.sender === 'user' ? (
                  msg.text
                ) : (
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-ucar-100 text-ucar-600 flex items-center justify-center shrink-0 shadow-sm">
                <Bot size={18} />
              </div>
              <div className="p-4 bg-white border border-slate-100 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1.5">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <form onSubmit={handleSend} className="p-3 bg-white border-t border-slate-100 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Posez une question à l'IA..."
            className="flex-1 bg-slate-100 border-transparent rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-ucar-500/20 focus:bg-white transition-all"
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={!input.trim() || loading}
            className="w-11 h-11 bg-ucar-600 text-white rounded-xl flex items-center justify-center hover:bg-ucar-700 disabled:opacity-50 disabled:hover:bg-ucar-600 transition-colors shadow-sm shrink-0"
          >
            <Send size={18} className="ml-1" />
          </button>
        </form>
      </div>
    </>
  );
}
