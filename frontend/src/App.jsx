import React, { useState } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import HowBisNovaHelps from './components/HowBisNovaHelps';
import StandardsAndLabs from './components/StandardsAndLabs';
import CtaBanner from './components/CtaBanner';
import Footer from './components/Footer';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import FAQPage from './components/FAQPage';
import ExploreStandardsPage from './components/ExploreStandardsPage';
import TestingLabsPage from './components/TestingLabsPage';
import { sendChatMessage, sendFeedback, BISNovaAPIError } from './api';
import { generateChatTitle } from './chatNaming';
import { markdownToPlainText } from './markdownToPlainText';

export default function App() {
  const [viewMode, setViewMode] = useState('landing'); // 'landing' | 'chatbot'
  // No pre-seeded chat history - a fresh visit (or "New Chat") always
  // starts as a blank composer with no active chat, matching Claude/
  // ChatGPT. A chat only gets created - and only appears in the sidebar
  // - once the user actually sends a first message (see
  // handleSendMessage's lazy-creation branch below).
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isSmiling, setIsSmiling] = useState(false);
  const [activeNav, setActiveNav] = useState('new-chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  let mascotState = 'idle';
  if (isSmiling) {
    mascotState = 'smiling';
  } else if (isThinking) {
    mascotState = 'thinking';
  } else if (isTyping) {
    mascotState = 'reading';
  }

  const activeChat = chats.find(c => c.id === activeChatId) || null;

  function handleToggleSidebar() {
    setIsSidebarOpen(prev => !prev);
  }

  // --- Maps a BISNova backend /api/chat response into the message shape
  //     MessageList already knows how to render ---
  function buildBotMessageFromResponse(apiResponse, userQuery) {
    const standardCards = (apiResponse.standards || []).map(std => ({
      code: std.is_number,
      title: std.title,
      mandatory: std.is_mandatory,
      relationship_type: std.relationship_type,
      lastVerified: std.last_verified,
    }));

    // Clarification options come back as ready-to-send follow-up queries -
    // they slot directly into the existing action-chip mechanism, no new
    // UI needed.
    const actionChips = apiResponse.needs_clarification
      ? (apiResponse.clarification_options || []).map(opt => ({
        label: opt.label,
        icon: '❓',
        query: opt.query,
      }))
      : null;

    const text = apiResponse.needs_clarification
      ? apiResponse.clarification_question
      : markdownToPlainText(apiResponse.answer);

    return {
      sender: 'bot',
      text,
      standardCards: standardCards.length > 0 ? standardCards : null,
      actionChips,
      confidenceLabel: apiResponse.confidence_label,
      sources: apiResponse.sources,
      disclaimer: apiResponse.disclaimer,
      // carried for the feedback buttons - see handleFeedback below
      feedbackQuery: userQuery,
      feedbackAnswer: apiResponse.answer,
      feedbackGiven: null,   // "up" | "down" | null, set after the user rates it
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isNew: true,
    };
  }

  // --- Send Message ---
  async function handleSendMessage(text, file = null) {
    if (!text && !file) return;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg = {
      sender: 'user',
      text: text || `Attached file: ${file.name}`,
      file: file ? { name: file.name } : null,
      time: currentTime,
      isNew: true
    };

    // Lazy chat creation: no chat exists yet until the user actually
    // sends something. This is the fix for "no chat that user didn't
    // create" - a fresh visit or a "New Chat" click never adds a
    // sidebar entry by itself, only a real sent message does. The
    // chat's own id doubles as the backend's session_id, so
    // conversation memory (see backend/session_store.py) is naturally
    // scoped per chat - no separate id generator needed.
    let targetChatId = activeChatId;
    if (!targetChatId) {
      targetChatId = `chat-${Date.now()}`;
      const newChat = {
        id: targetChatId,
        title: generateChatTitle(text || file?.name || 'New Chat'),
        pinned: false,
        messages: [userMsg],
      };
      setChats(prevChats => [newChat, ...prevChats]);
      setActiveChatId(targetChatId);
    } else {
      setChats(prevChats =>
        prevChats.map(c =>
          c.id === targetChatId
            ? { ...c, messages: [...c.messages, userMsg] }
            : c
        )
      );
    }

    setIsThinking(true);
    setIsTyping(false);

    // File attachments aren't wired to the backend yet (out of current
    // scope) - only text queries are sent.
    if (!text) {
      setIsThinking(false);
      return;
    }

    try {
      const apiResponse = await sendChatMessage(text, targetChatId);
      const botMsg = buildBotMessageFromResponse(apiResponse, text);

      setIsThinking(false);
      setIsSmiling(true);

      setChats(prevChats =>
        prevChats.map(c =>
          c.id === targetChatId
            ? { ...c, messages: [...c.messages, botMsg] }
            : c
        )
      );

      setTimeout(() => setIsSmiling(false), 1200);
    } catch (err) {
      setIsThinking(false);

      const message = err instanceof BISNovaAPIError
        ? err.message
        : "Something went wrong on my end. Please try again in a moment.";

      const errorMsg = {
        sender: 'bot',
        text: message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isNew: true,
      };

      setChats(prevChats =>
        prevChats.map(c =>
          c.id === targetChatId
            ? { ...c, messages: [...c.messages, errorMsg] }
            : c
        )
      );
    }
  }

  function handleOpenChatbotWithQuery(query) {
    setViewMode('chatbot');
    setTimeout(() => {
      handleSendMessage(query);
    }, 200);
  }

  async function handleFeedback(chatId, messageIndex, rating) {
    // Optimistically mark it in the UI immediately
    setChats(prevChats =>
      prevChats.map(c =>
        c.id === chatId
          ? {
            ...c,
            messages: c.messages.map((m, i) =>
              i === messageIndex ? { ...m, feedbackGiven: rating } : m
            ),
          }
          : c
      )
    );

    const chat = chats.find(c => c.id === chatId);
    const msg = chat?.messages[messageIndex];
    if (!msg) return;

    try {
      await sendFeedback({
        query: msg.feedbackQuery || '',
        answer: msg.feedbackAnswer || msg.text,
        rating,
        sessionId: chatId,
      });
    } catch (err) {
      // Feedback failing silently is fine - it's not critical path, and
      // we don't want a failed 👍/👎 to interrupt the conversation.
    }
  }

  function handleNewChat() {
    // Just reset to a blank composer - do NOT create a chat record yet.
    // A sidebar entry only appears once the user actually sends a
    // message (see handleSendMessage's lazy-creation branch) - this is
    // the fix for "there should not be any chat that user didn't create".
    setActiveChatId(null);
    setActiveNav('new-chat');
  }

  function handleClearChat() {
    if (confirm('Clear messages in this conversation?')) {
      setChats(prev =>
        prev.map(c =>
          c.id === activeChatId
            ? {
              ...c,
              messages: [
                {
                  sender: 'bot',
                  text: "Conversation cleared. Ask me anything about Indian Standards, testing, or BIS certification!",
                  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ]
            }
            : c
        )
      );
    }
  }

  function handlePinChat(chatId) {
    setChats(prev =>
      prev.map(c => (c.id === chatId ? { ...c, pinned: !c.pinned } : c))
    );
  }

  function handleRenameChat(chatId, newTitle) {
    setChats(prev =>
      prev.map(c => (c.id === chatId ? { ...c, title: newTitle } : c))
    );
  }

  function handleDeleteChat(chatId) {
    setChats(prev => prev.filter(c => c.id !== chatId));

    if (activeChatId === chatId) {
      const remaining = chats.filter(c => c.id !== chatId);
      // Fall back to a blank composer (no chat selected), not a
      // fabricated placeholder chat - same "no chat the user didn't
      // create" principle as handleNewChat().
      setActiveChatId(remaining.length > 0 ? remaining[0].id : null);
    }
  }

  function handleSelectChat(chatId) {
    setActiveChatId(chatId);
  }

  function handleNavClick(name) {
    setActiveNav(name);

    // These previously all sent meta-text like "Open Dashboard" as if it
    // were a real user question - harmless against the old mock responder,
    // but confusing now that this hits the real backend (which would
    // honestly, correctly, return "not_found" for text that isn't an
    // actual product question). Route each to something real instead.
    if (name === 'Other Queries / FAQs') {
      setViewMode('faq');
      return;
    }

    if (name === 'Explore Standards') {
      setViewMode('explore-standards');
      return;
    }

    if (name === 'Testing and Labs') {
      setViewMode('testing-labs');
      return;
    }

    if (name === 'Dashboard') {
      // No dashboard page/design exists yet - safe no-op (fresh chat)
      // rather than sending meaningless text to the real backend.
      handleNewChat();
      return;
    }

    handleOpenChatbotWithQuery(`Tell me about ${name}`);
  }

  function handleMascotClick() {
    setIsSmiling(true);
    setTimeout(() => setIsSmiling(false), 1200);
  }

  function handleNavigateSection(sectionId) {
    // Full FAQ page
    if (sectionId === 'faq-page') {
      setViewMode('faq');
      return;
    }

    // Explore Standards is a dedicated page, not a landing-page section
    if (sectionId === 'explore-standards') {
      setViewMode('explore-standards');
      return;
    }
    if (sectionId === 'testing-labs') {
      setViewMode('testing-labs');
      return;
    }

    // Return to landing page when needed
    if (sectionId === 'home-page' || sectionId === 'hero') {
      setViewMode('landing');
      setTimeout(() => {
        const el = document.getElementById('hero');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth' });
        }
      }, 50);
      return;
    }

    // Any other landing-page section target (e.g. 'how-bisnova-helps',
    // 'standards-labs'). BUG FIX: these DOM nodes only exist while the
    // landing page is actually rendered - if the user is currently on
    // the FAQ page or Explore Standards page, clicking a section link
    // silently did nothing, because document.getElementById() couldn't
    // find an element that isn't mounted. Fix: switch to the landing
    // page first, wait for it to render, then scroll.
    if (viewMode !== 'landing') {
      setViewMode('landing');
      setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth' });
        }
      }, 50);
      return;
    }

    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  }

  // =========================================================================
  // Render FAQ Page View
  // =========================================================================
  if (viewMode === 'faq') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
          viewMode={viewMode}
        />

        <FAQPage
          onOpenChatbot={() => setViewMode('chatbot')}
        />

        <Footer
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
        />
      </div>
    );
  }

  // =========================================================================
  // Render Explore Standards Page View
  // =========================================================================
  if (viewMode === 'explore-standards') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
          viewMode={viewMode}
        />

        <ExploreStandardsPage
          onAskAboutStandard={handleOpenChatbotWithQuery}
        />

        <Footer
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
        />
      </div>
    );
  }

  // TODO: Testing and Labs page dalega yaha
  // =========================================================================
  // Render Testing & Labs Page View
  // =========================================================================

  if (viewMode === 'testing-labs') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
          viewMode={viewMode}
        />

        <TestingLabsPage
          onOpenChatbot={handleOpenChatbotWithQuery}
        />

        <Footer
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
        />
      </div>
    );

  }

  // =========================================================================
  // Render Landing Page View
  // =========================================================================
  if (viewMode === 'landing') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() => setViewMode('chatbot')}
          onNavigateSection={handleNavigateSection}
          viewMode={viewMode}
        />

        <main className="landing-main-content">
          <HeroSection
            onOpenChatbot={() => setViewMode('chatbot')}
            onExploreStandards={() => setViewMode('explore-standards')}
          />

          <HowBisNovaHelps
            onOpenChatbotWithQuery={handleOpenChatbotWithQuery}
          />

          <StandardsAndLabs
            onOpenChatbotWithQuery={handleOpenChatbotWithQuery}
            onExploreStandards={() => setViewMode('explore-standards')}
          />

          <CtaBanner
            onOpenChatbot={() => setViewMode('chatbot')}
          />
        </main>

        <Footer onOpenChatbot={() => setViewMode('chatbot')} onNavigateSection={handleNavigateSection} />
      </div>
    );
  }

  // =========================================================================
  // Render Chatbot View
  // =========================================================================
  return (
    <div className="app-container">
      {/* Mobile Drawer Backdrop */}
      {isSidebarOpen && (
        <div
          className="sidebar-overlay active"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={handleToggleSidebar}
        onCloseMobile={() => setIsSidebarOpen(false)}
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onPinChat={handlePinChat}
        onRenameChat={handleRenameChat}
        onDeleteChat={handleDeleteChat}
        onNavClick={handleNavClick}
        activeNav={activeNav}
        mascotState={mascotState}
        onMascotClick={handleMascotClick}
      />

      {/* Main Chat Area */}
      <main className="chat-main">
        <ChatHeader
          onToggleSidebar={handleToggleSidebar}
          onGoHome={() => setViewMode('landing')}
          onClearChat={handleClearChat}
        />

        <MessageList
          messages={activeChat ? activeChat.messages : []}
          isThinking={isThinking}
          onChipClick={(query) => handleSendMessage(query)}
          onFeedback={(messageIndex, rating) => handleFeedback(activeChatId, messageIndex, rating)}
        />

        <ChatInput
          onSendMessage={handleSendMessage}
          onTypingChange={(typing) => setIsTyping(typing)}
          onSelectSuggestion={(query) => handleSendMessage(query)}
        />

        <p className="chat-disclaimer-footer">
          Informational guidance only — not a substitute for official BIS
          certification advice.
        </p>
      </main>
    </div>
  );
}
