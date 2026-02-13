"use client";

import { useState, useRef, useEffect } from "react";
import { Send, User } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const AVATAR_SRC = "/hopeogbons.png";

const CONVERSATION_STARTERS = [
  "What does a Forward-Deployed AI Engineer do?",
  "Tell me about your multi-agent projects",
  "How do you prevent LLM hallucinations in production?",
  "What industries have you built AI systems for?",
];

export default function Twin() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const sendMessage = async (text?: string) => {
    const messageText = text || input;
    if (!messageText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: messageText,
            session_id: sessionId || undefined,
          }),
        }
      );

      if (!response.ok) throw new Error("Failed to send message");

      const data = await response.json();

      if (!sessionId) {
        setSessionId(data.session_id);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 rounded-lg shadow-lg">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white p-4 rounded-t-lg flex items-center gap-3">
        <div className="relative">
          <img
            src={AVATAR_SRC}
            alt="Hope Ogbons"
            className="w-10 h-10 rounded-full object-cover object-top ring-2 ring-slate-500"
          />
          <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 border-2 border-slate-700 rounded-full" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">AI Digital Twin</h2>
          <p className="text-sm text-slate-300">by Hope Ogbons</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <img
              src={AVATAR_SRC}
              alt="Hope Ogbons"
              className="w-16 h-16 rounded-full object-cover object-top ring-4 ring-gray-200 mx-auto mb-3"
            />
            <p className="font-medium text-gray-700">
              Hello! I&apos;m Hope&apos;s Digital Twin.
            </p>
            <p className="text-sm mt-1 mb-6">
              Ask me anything about AI, cloud, or engineering!
            </p>

            {/* Conversation Starters */}
            <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
              {CONVERSATION_STARTERS.map((starter) => (
                <button
                  key={starter}
                  onClick={() => sendMessage(starter)}
                  className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-full text-gray-700 hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm"
                >
                  {starter}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role === "assistant" && (
              <div className="flex-shrink-0">
                <img
                  src={AVATAR_SRC}
                  alt="Hope Ogbons"
                  className="w-8 h-8 rounded-full object-cover object-top ring-2 ring-gray-200"
                />
              </div>
            )}

            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-slate-700 text-white"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              {message.role === "assistant" ? (
                <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-headings:my-2 prose-pre:bg-gray-100 prose-pre:text-gray-800 prose-code:text-slate-700 prose-code:before:content-none prose-code:after:content-none">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}
              <p
                className={`text-xs mt-1 ${
                  message.role === "user" ? "text-slate-300" : "text-gray-500"
                }`}
              >
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>

            {message.role === "user" && (
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center ring-2 ring-gray-300">
                  <User className="w-5 h-5 text-white" />
                </div>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0">
              <img
                src={AVATAR_SRC}
                alt="Hope Ogbons"
                className="w-8 h-8 rounded-full object-cover object-top ring-2 ring-gray-200"
              />
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 bg-white rounded-b-lg">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Type your message..."
            rows={1}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-600 focus:border-transparent text-gray-800 resize-none overflow-hidden"
            disabled={isLoading}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
