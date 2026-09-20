import React, { useState, useEffect } from 'react';
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
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import AdminDashboard from './components/AdminDashboard';
import { useAuth } from './AuthContext';

import {
  sendChatMessage,
  sendFeedback,
  fetchChatHistory,
  fetchChatSessions,
  deleteChatHistory,
  BISNovaAPIError,
} from './api';

import { generateChatTitle } from './chatNaming';
import { markdownToPlainText } from './markdownToPlainText';

export default function App() {
  const [viewMode, setViewMode] = useState('landing');

  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);

  const [isThinking, setIsThinking] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isSmiling, setIsSmiling] = useState(false);

  const [activeNav, setActiveNav] =
    useState('new-chat');

  const [isSidebarOpen, setIsSidebarOpen] =
    useState(true);

  // IMPORTANT:
  // Saving to localStorage is disabled until the current
  // user's local + DB history has finished loading.
  const [hydratedUserId, setHydratedUserId] =
    useState(null);

  const {
    user,
    token,
    isAdmin,
    logout,
    sessionExpired,
    clearSessionExpired,
  } = useAuth();

  // ============================================================
  // USER-SPECIFIC STORAGE KEY
  // ============================================================

  function getChatStorageKey(userId) {
    if (!userId) return null;

    return `bisnova_chat_sessions_${userId}`;
  }

  // ============================================================
  // MERGE DATABASE HISTORY INTO A LOCAL CHAT
  // ============================================================

  function mergeDatabaseHistoryIntoChat(
    localChat,
    history
  ) {
    if (
      !localChat ||
      !Array.isArray(history) ||
      history.length === 0
    ) {
      return localChat;
    }

    const localMessages =
      Array.isArray(localChat.messages)
        ? localChat.messages
        : [];

    const mergedMessages =
      history.map((dbMessage, index) => {
        const existingMessage =
          localMessages[index];

        const sender =
          dbMessage.role === 'user'
            ? 'user'
            : 'bot';

        // Preserve richer locally stored UI data
        // whenever role/content still match.
        if (
          existingMessage &&
          existingMessage.sender === sender &&
          (
            existingMessage.text ===
              dbMessage.content ||
            markdownToPlainText(
              existingMessage.text || ''
            ) ===
              markdownToPlainText(
                dbMessage.content || ''
              )
          )
        ) {
          return {
            ...existingMessage,
            sender,
            text:
              existingMessage.text ||
              dbMessage.content,
          };
        }

        // DB-only message.
        return {
          sender,
          text: dbMessage.content,
          time: dbMessage.created_at
            ? new Date(
                dbMessage.created_at
              ).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })
            : '',
          isNew: false,
        };
      });

    return {
      ...localChat,
      messages: mergedMessages,
    };
  }

  // ============================================================
  // CREATE A FRONTEND CHAT FROM DB HISTORY
  //
  // Used when a session exists in DB but does not exist in
  // localStorage. This enables cross-device recovery.
  // ============================================================

  function createChatFromDatabaseHistory(
    session,
    history
  ) {
    if (
      !session?.session_id ||
      !Array.isArray(history) ||
      history.length === 0
    ) {
      return null;
    }

    const firstUserMessage =
      history.find(
        (message) =>
          message.role === 'user'
      );

    const titleSource =
      firstUserMessage?.content ||
      'New Chat';

    const messages =
      history.map((dbMessage) => ({
        sender:
          dbMessage.role === 'user'
            ? 'user'
            : 'bot',

        text: dbMessage.content,

        time: dbMessage.created_at
          ? new Date(
              dbMessage.created_at
            ).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })
          : '',

        isNew: false,
      }));

    return {
      id: session.session_id,

      title:
        generateChatTitle(
          titleSource
        ),

      pinned: false,

      messages,
    };
  }

  // ============================================================
  // LOAD CURRENT USER'S CHATS
  //
  // 1. Load user-specific localStorage.
  // 2. Ask DB for ALL sessions belonging to JWT user.
  // 3. Combine local sessions + DB sessions.
  // 4. Fetch DB history for every discovered session.
  // 5. Preserve rich local UI data whenever possible.
  // 6. Create frontend chats for DB-only sessions.
  // 7. Only then mark hydration complete.
  // ============================================================

  useEffect(() => {
    if (!user?.id) {
      setHydratedUserId(null);
      setChats([]);
      setActiveChatId(null);
      return;
    }

    const storageKey =
      getChatStorageKey(user.id);

    // Disable localStorage saving while loading.
    setHydratedUserId(null);

    let cancelled = false;

    async function loadUserChats() {
      let storedChats = [];

      // --------------------------------------------------------
      // STEP 1: LOAD LOCAL USER-SPECIFIC CHATS
      // --------------------------------------------------------

      try {
        const raw =
          localStorage.getItem(storageKey);

        if (raw) {
          const parsed = JSON.parse(raw);

          if (Array.isArray(parsed)) {
            storedChats = parsed;
          }
        }
      } catch (error) {
        console.error(
          'Failed to load saved chats:',
          error
        );

        storedChats = [];
      }

      if (cancelled) return;

      // Show local chats immediately.
      setChats(storedChats);
      setActiveChatId(null);

      // --------------------------------------------------------
      // STEP 2: DISCOVER ALL DB SESSIONS FOR THIS USER
      // --------------------------------------------------------

      let dbSessions = [];

      if (token) {
        try {
          dbSessions =
            await fetchChatSessions(token);
        } catch (error) {
          console.warn(
            'Could not retrieve DB chat sessions:',
            error
          );

          dbSessions = [];
        }
      }

      if (cancelled) return;

      // --------------------------------------------------------
      // STEP 3: BUILD UNIQUE SESSION ID LIST
      // --------------------------------------------------------

      const sessionMap =
        new Map();

      // Local sessions first so rich UI data remains available.
      storedChats.forEach((chat) => {
        sessionMap.set(
          chat.id,
          {
            session_id: chat.id,
            localChat: chat,
            dbSession: null,
          }
        );
      });

      // Add DB-only sessions.
      dbSessions.forEach((session) => {
        const existing =
          sessionMap.get(
            session.session_id
          );

        if (existing) {
          existing.dbSession = session;
        } else {
          sessionMap.set(
            session.session_id,
            {
              session_id:
                session.session_id,
              localChat: null,
              dbSession: session,
            }
          );
        }
      });

      const discoveredSessions =
        Array.from(
          sessionMap.values()
        );

      // --------------------------------------------------------
      // STEP 4: FETCH DB HISTORY FOR EVERY SESSION
      // --------------------------------------------------------

      let restoredChats = [];

      if (
        token &&
        discoveredSessions.length > 0
      ) {
        const results =
          await Promise.all(
            discoveredSessions.map(
              async (sessionInfo) => {
                try {
                  const history =
                    await fetchChatHistory(
                      sessionInfo.session_id,
                      token
                    );

                  return {
                    ...sessionInfo,
                    history,
                  };
                } catch (error) {
                  console.warn(
                    `Could not restore DB history for chat ${sessionInfo.session_id}:`,
                    error
                  );

                  return {
                    ...sessionInfo,
                    history: null,
                  };
                }
              }
            )
          );

        if (cancelled) return;

        // ------------------------------------------------------
        // STEP 5: MERGE LOCAL + DB
        // ------------------------------------------------------

        restoredChats =
          results
            .map(
              ({
                session_id,
                localChat,
                dbSession,
                history,
              }) => {
                // Local + DB history.
                if (
                  localChat &&
                  Array.isArray(history) &&
                  history.length > 0
                ) {
                  return mergeDatabaseHistoryIntoChat(
                    localChat,
                    history
                  );
                }

                // DB-only session.
                if (
                  !localChat &&
                  dbSession &&
                  Array.isArray(history) &&
                  history.length > 0
                ) {
                  return createChatFromDatabaseHistory(
                    dbSession,
                    history
                  );
                }

                // Local-only chat.
                if (localChat) {
                  return localChat;
                }

                return null;
              }
            )
            .filter(Boolean);
      } else {
        // No token / DB unavailable.
        // Preserve local chats.
        restoredChats = storedChats;
      }

      if (cancelled) return;

      // --------------------------------------------------------
      // STEP 6: UPDATE CHAT STATE
      // --------------------------------------------------------

      setChats(restoredChats);

      // Do not automatically select a chat after login/refresh.
      setActiveChatId(null);

      // --------------------------------------------------------
      // STEP 7: ALLOW LOCAL STORAGE SAVING
      // --------------------------------------------------------

      setHydratedUserId(user.id);
    }

    loadUserChats();

    return () => {
      cancelled = true;
    };
  }, [user?.id, token]);

  // ============================================================
  // SAVE CURRENT USER'S CHATS
  // ============================================================

  useEffect(() => {
    if (!user?.id) return;

    if (hydratedUserId !== user.id) {
      return;
    }

    const storageKey =
      getChatStorageKey(user.id);

    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify(chats)
      );
    } catch (error) {
      console.error(
        'Failed to save chats:',
        error
      );
    }
  }, [
    chats,
    user?.id,
    hydratedUserId,
  ]);

  // ============================================================
  // SESSION EXPIRY
  // ============================================================

  useEffect(() => {
    if (sessionExpired) {
      setViewMode('login');
      clearSessionExpired();
    }
  }, [
    sessionExpired,
    clearSessionExpired,
  ]);

  // ============================================================
  // MASCOT STATE
  // ============================================================

  let mascotState = 'idle';

  if (isSmiling) {
    mascotState = 'smiling';
  } else if (isThinking) {
    mascotState = 'thinking';
  } else if (isTyping) {
    mascotState = 'reading';
  }

  const activeChat =
    chats.find(
      (c) => c.id === activeChatId
    ) || null;

  // ============================================================
  // SIDEBAR
  // ============================================================

  function handleToggleSidebar() {
    setIsSidebarOpen(
      (prev) => !prev
    );
  }

  // ============================================================
  // STANDARD CODE CLEANUP
  // ============================================================

  function cleanStandardCode(rawCode) {
    if (!rawCode) return rawCode;

    return rawCode.replace(
      /^(IS\s+)+/i,
      'IS '
    );
  }

  // ============================================================
  // BUILD BOT MESSAGE
  // ============================================================

  function buildBotMessageFromResponse(
    apiResponse,
    userQuery
  ) {
    const standardCards = (
      apiResponse.standards || []
    ).map((std) => ({
      code: cleanStandardCode(
        std.is_number
      ),
      title: std.title,
      mandatory: std.is_mandatory,
      relationship_type:
        std.relationship_type,
      lastVerified:
        std.last_verified,
      sourceUrl: std.source_url,
    }));

    const actionChips =
      apiResponse.needs_clarification
        ? (
            apiResponse.clarification_options ||
            []
          ).map((opt) => ({
            label: opt.label,
            icon: '🔍',
            query: opt.query,
          }))
        : null;

    const text =
      apiResponse.needs_clarification
        ? apiResponse.clarification_question
        : markdownToPlainText(
            apiResponse.answer
          );

    return {
      sender: 'bot',
      text,

      standardCards:
        standardCards.length > 0
          ? standardCards
          : null,

      actionChips,

      confidenceLabel:
        apiResponse.confidence_label,

      sources:
        apiResponse.sources,

      disclaimer:
        apiResponse.disclaimer,

      feedbackQuery: userQuery,

      feedbackAnswer:
        apiResponse.answer,

      feedbackGiven: null,

      time:
        new Date().toLocaleTimeString(
          [],
          {
            hour: '2-digit',
            minute: '2-digit',
          }
        ),

      isNew: true,
    };
  }

  // ============================================================
  // SEND MESSAGE
  // ============================================================

  async function handleSendMessage(
    text,
    file = null
  ) {
    if (!text && !file) return;

    // Protected /api/chat requires JWT.
    if (!token) {
      setViewMode('login');
      return;
    }

    const currentTime =
      new Date().toLocaleTimeString(
        [],
        {
          hour: '2-digit',
          minute: '2-digit',
        }
      );

    const userMsg = {
      sender: 'user',

      text:
        text ||
        `Attached file: ${file.name}`,

      file: file
        ? {
            name: file.name,
          }
        : null,

      time: currentTime,

      isNew: true,
    };

    // ==========================================================
    // CREATE NEW CHAT ONLY WHEN FIRST MESSAGE IS SENT
    // ==========================================================

    let targetChatId =
      activeChatId;

    if (!targetChatId) {
      targetChatId =
        crypto.randomUUID();

      const newChat = {
        id: targetChatId,

        title: generateChatTitle(
          text ||
            file?.name ||
            'New Chat'
        ),

        pinned: false,

        messages: [userMsg],
      };

      setChats((prevChats) => [
        newChat,
        ...prevChats,
      ]);

      setActiveChatId(
        targetChatId
      );
    } else {
      setChats((prevChats) =>
        prevChats.map((c) =>
          c.id === targetChatId
            ? {
                ...c,

                messages: [
                  ...c.messages,
                  userMsg,
                ],
              }
            : c
        )
      );
    }

    setIsThinking(true);
    setIsTyping(false);

    // File uploads are not connected yet.
    if (!text) {
      setIsThinking(false);
      return;
    }

    try {
      const apiResponse =
        await sendChatMessage(
          text,
          targetChatId,
          token
        );

      const botMsg =
        buildBotMessageFromResponse(
          apiResponse,
          text
        );

      setIsThinking(false);
      setIsSmiling(true);

      setChats((prevChats) =>
        prevChats.map((c) =>
          c.id === targetChatId
            ? {
                ...c,

                messages: [
                  ...c.messages,
                  botMsg,
                ],
              }
            : c
        )
      );

      setTimeout(() => {
        setIsSmiling(false);
      }, 1200);
    } catch (err) {
      setIsThinking(false);

      const message =
        err instanceof BISNovaAPIError
          ? err.message
          : 'Something went wrong on my end. Please try again in a moment.';

      const errorMsg = {
        sender: 'bot',

        text: message,

        time:
          new Date().toLocaleTimeString(
            [],
            {
              hour: '2-digit',
              minute: '2-digit',
            }
          ),

        isNew: true,
      };

      setChats((prevChats) =>
        prevChats.map((c) =>
          c.id === targetChatId
            ? {
                ...c,

                messages: [
                  ...c.messages,
                  errorMsg,
                ],
              }
            : c
        )
      );
    }
  }

  // ============================================================
  // OPEN CHAT WITH QUERY
  // ============================================================

  function handleOpenChatbotWithQuery(
    query
  ) {
    setViewMode('chatbot');

    setTimeout(() => {
      handleSendMessage(query);
    }, 200);
  }

  // ============================================================
  // FEEDBACK
  // ============================================================

  async function handleFeedback(
    chatId,
    messageIndex,
    rating
  ) {
    setChats((prevChats) =>
      prevChats.map((c) =>
        c.id === chatId
          ? {
              ...c,

              messages:
                c.messages.map(
                  (m, i) =>
                    i === messageIndex
                      ? {
                          ...m,
                          feedbackGiven:
                            rating,
                        }
                      : m
                ),
            }
          : c
      )
    );

    const chat = chats.find(
      (c) => c.id === chatId
    );

    const msg =
      chat?.messages[
        messageIndex
      ];

    if (!msg) return;

    try {
      await sendFeedback(
        msg.feedbackQuery || '',
        msg.feedbackAnswer ||
          msg.text,
        rating,
        chatId,
        null
      );
    } catch (err) {
      // Feedback is non-critical.
    }
  }

  // ============================================================
  // NEW CHAT
  // ============================================================

  function handleNewChat() {
    setActiveChatId(null);
    setActiveNav('new-chat');
  }

  // ============================================================
  // CLEAR CHAT
  //
  // IMPORTANT:
  // Clear now removes the conversation from BOTH:
  // 1. Supabase DB
  // 2. Frontend/localStorage
  //
  // This prevents the old conversation from returning
  // after page refresh.
  // ============================================================

  async function handleClearChat() {
    if (!activeChatId) {
      return;
    }

    if (
      !confirm(
        'Clear messages in this conversation?'
      )
    ) {
      return;
    }

    if (!token) {
      setViewMode('login');
      return;
    }

    const chatIdToClear =
      activeChatId;

    try {
      // Delete DB history first.
      await deleteChatHistory(
        chatIdToClear,
        token
      );

      // Remove the conversation from frontend state.
      setChats((prevChats) =>
        prevChats.filter(
          (chat) =>
            chat.id !== chatIdToClear
        )
      );

      // Return to blank new-chat state.
      setActiveChatId(null);
      setActiveNav('new-chat');
    } catch (error) {
      console.error(
        'Failed to clear chat:',
        error
      );

      if (
        error instanceof BISNovaAPIError &&
        error.status === 401
      ) {
        setViewMode('login');
        return;
      }

      alert(
        error?.message ||
          'Could not clear this conversation. Please try again.'
      );
    }
  }

  // ============================================================
  // PIN CHAT
  // ============================================================

  function handlePinChat(chatId) {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? {
              ...c,
              pinned: !c.pinned,
            }
          : c
      )
    );
  }

  // ============================================================
  // RENAME CHAT
  // ============================================================

  function handleRenameChat(
    chatId,
    newTitle
  ) {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? {
              ...c,
              title: newTitle,
            }
          : c
      )
    );
  }

  // ============================================================
  // DELETE CHAT
  //
  // IMPORTANT:
  // Delete now removes the conversation from BOTH:
  // 1. Supabase DB
  // 2. Frontend/localStorage
  // ============================================================

  async function handleDeleteChat(
    chatId
  ) {
    if (!chatId) {
      return;
    }

    if (
      !confirm(
        'Delete this conversation permanently?'
      )
    ) {
      return;
    }

    if (!token) {
      setViewMode('login');
      return;
    }

    try {
      // Delete DB history first.
      await deleteChatHistory(
        chatId,
        token
      );

      // Remove from frontend state.
      setChats((prevChats) => {
        const remaining =
          prevChats.filter(
            (chat) =>
              chat.id !== chatId
          );

        // If deleted chat was active,
        // open another remaining chat if available.
        if (
          activeChatId === chatId
        ) {
          setActiveChatId(
            remaining.length > 0
              ? remaining[0].id
              : null
          );
        }

        return remaining;
      });
    } catch (error) {
      console.error(
        'Failed to delete chat:',
        error
      );

      if (
        error instanceof BISNovaAPIError &&
        error.status === 401
      ) {
        setViewMode('login');
        return;
      }

      alert(
        error?.message ||
          'Could not delete this conversation. Please try again.'
      );
    }
  }

  // ============================================================
  // SELECT CHAT
  // ============================================================

  function handleSelectChat(chatId) {
    setActiveChatId(chatId);
  }

  // ============================================================
  // SIDEBAR NAVIGATION
  // ============================================================

  function handleNavClick(name) {
    setActiveNav(name);

    if (
      name ===
      'Other Queries / FAQs'
    ) {
      setViewMode('faq');
      return;
    }

    if (
      name ===
      'Explore Standards'
    ) {
      setViewMode(
        'explore-standards'
      );
      return;
    }

    if (
      name ===
      'Testing and Labs'
    ) {
      handleOpenChatbotWithQuery(
        'Where can I get my product tested?'
      );
      return;
    }

    if (name === 'Dashboard') {
      handleNewChat();
      return;
    }

    handleOpenChatbotWithQuery(
      `Tell me about ${name}`
    );
  }

  // ============================================================
  // LOGOUT
  // ============================================================

  function handleLogout() {
    // Clear React state only.
    //
    // IMPORTANT:
    // Do NOT delete localStorage here.
    //
    // User-specific local chats remain under:
    // bisnova_chat_sessions_<user-id>
    //
    // DB history remains protected by JWT.

    setChats([]);
    setActiveChatId(null);
    setHydratedUserId(null);

    logout();

    setViewMode('landing');
  }

  // ============================================================
  // MASCOT
  // ============================================================

  function handleMascotClick() {
    setIsSmiling(true);

    setTimeout(() => {
      setIsSmiling(false);
    }, 1200);
  }

  // ============================================================
  // NAVIGATION
  // ============================================================

  function handleNavigateSection(
    sectionId
  ) {
    if (
      sectionId === 'faq-page'
    ) {
      setViewMode('faq');
      return;
    }

    if (
      sectionId ===
      'explore-standards'
    ) {
      setViewMode(
        'explore-standards'
      );
      return;
    }

    if (
      sectionId === 'home-page' ||
      sectionId === 'hero'
    ) {
      setViewMode('landing');

      setTimeout(() => {
        const el =
          document.getElementById(
            'hero'
          );

        if (el) {
          el.scrollIntoView({
            behavior: 'smooth',
          });
        }
      }, 50);

      return;
    }

    if (
      viewMode !== 'landing'
    ) {
      setViewMode('landing');

      setTimeout(() => {
        const el =
          document.getElementById(
            sectionId
          );

        if (el) {
          el.scrollIntoView({
            behavior: 'smooth',
          });
        }
      }, 50);

      return;
    }

    const el =
      document.getElementById(
        sectionId
      );

    if (el) {
      el.scrollIntoView({
        behavior: 'smooth',
      });
    }
  }

  // ============================================================
  // FAQ PAGE
  // ============================================================

  if (viewMode === 'faq') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
          viewMode={viewMode}
          user={user}
          isAdmin={isAdmin}
          onLogout={handleLogout}
          onGoToLogin={() =>
            setViewMode('login')
          }
          onGoToRegister={() =>
            setViewMode('register')
          }
          onGoToAdmin={() =>
            setViewMode('admin')
          }
        />

        <FAQPage
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
        />

        <Footer
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
        />
      </div>
    );
  }

  // ============================================================
  // EXPLORE STANDARDS
  // ============================================================

  if (
    viewMode ===
    'explore-standards'
  ) {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
          viewMode={viewMode}
          user={user}
          isAdmin={isAdmin}
          onLogout={handleLogout}
          onGoToLogin={() =>
            setViewMode('login')
          }
          onGoToRegister={() =>
            setViewMode('register')
          }
          onGoToAdmin={() =>
            setViewMode('admin')
          }
        />

        <ExploreStandardsPage
          onAskAboutStandard={
            handleOpenChatbotWithQuery
          }
        />

        <Footer
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
        />
      </div>
    );
  }

  // ============================================================
  // LOGIN
  // ============================================================

  if (viewMode === 'login') {
    return (
      <LoginPage
        onLoginSuccess={() =>
          setViewMode('landing')
        }
        onGoToRegister={() =>
          setViewMode('register')
        }
        onBack={() =>
          setViewMode('landing')
        }
      />
    );
  }

  // ============================================================
  // REGISTER
  // ============================================================

  if (
    viewMode === 'register'
  ) {
    return (
      <RegisterPage
        onGoToLogin={() =>
          setViewMode('login')
        }
        onBack={() =>
          setViewMode('landing')
        }
      />
    );
  }

  // ============================================================
  // ADMIN
  // ============================================================

  if (viewMode === 'admin') {
    if (!isAdmin) {
      setViewMode('landing');
      return null;
    }

    return (
      <AdminDashboard
        onBack={() =>
          setViewMode('landing')
        }
      />
    );
  }

  // ============================================================
  // LANDING PAGE
  // ============================================================

  if (viewMode === 'landing') {
    return (
      <div className="landing-page-root">
        <Navbar
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
          viewMode={viewMode}
          user={user}
          isAdmin={isAdmin}
          onLogout={handleLogout}
          onGoToLogin={() =>
            setViewMode('login')
          }
          onGoToRegister={() =>
            setViewMode('register')
          }
          onGoToAdmin={() =>
            setViewMode('admin')
          }
        />

        <main className="landing-main-content">
          <HeroSection
            onOpenChatbot={() =>
              setViewMode('chatbot')
            }
            onExploreStandards={() =>
              setViewMode(
                'explore-standards'
              )
            }
          />

          <HowBisNovaHelps
            onOpenChatbotWithQuery={
              handleOpenChatbotWithQuery
            }
          />

          <StandardsAndLabs
            onOpenChatbotWithQuery={
              handleOpenChatbotWithQuery
            }
            onExploreStandards={() =>
              setViewMode(
                'explore-standards'
              )
            }
          />

          <CtaBanner
            onOpenChatbot={() =>
              setViewMode('chatbot')
            }
          />
        </main>

        <Footer
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
          onNavigateSection={
            handleNavigateSection
          }
        />
      </div>
    );
  }

  // ============================================================
  // CHATBOT
  // ============================================================

  return (
    <div className="app-container">
      {isSidebarOpen && (
        <div
          className="sidebar-overlay active"
          onClick={() =>
            setIsSidebarOpen(false)
          }
        />
      )}

      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={
          handleToggleSidebar
        }
        onCloseMobile={() =>
          setIsSidebarOpen(false)
        }
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={
          handleSelectChat
        }
        onNewChat={handleNewChat}
        onPinChat={handlePinChat}
        onRenameChat={
          handleRenameChat
        }
        onDeleteChat={
          handleDeleteChat
        }
        onNavClick={
          handleNavClick
        }
        activeNav={activeNav}
        mascotState={mascotState}
        onMascotClick={
          handleMascotClick
        }
      />

      <main className="chat-main">
        <ChatHeader
          onToggleSidebar={
            handleToggleSidebar
          }
          onGoHome={() =>
            setViewMode('landing')
          }
          onClearChat={
            handleClearChat
          }
        />

        <MessageList
          messages={
            activeChat
              ? activeChat.messages
              : []
          }
          isThinking={isThinking}
          onChipClick={(query) =>
            handleSendMessage(query)
          }
          onFeedback={(
            messageIndex,
            rating
          ) =>
            handleFeedback(
              activeChatId,
              messageIndex,
              rating
            )
          }
        />

        <ChatInput
          onSendMessage={
            handleSendMessage
          }
          onTypingChange={(
            typing
          ) =>
            setIsTyping(typing)
          }
          onSelectSuggestion={(
            query
          ) =>
            handleSendMessage(query)
          }
        />

        <p className="chat-disclaimer-footer">
          Informational guidance only —
          not a substitute for official
          BIS certification advice.
        </p>
      </main>
    </div>
  );
}