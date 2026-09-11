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

import {
  sendChatMessage,
  BISNovaAPIError
} from './api';


// ============================================================================
// INITIAL CHAT
// ============================================================================

const INITIAL_CHATS = [
  {
    id: '1',
    title: 'New Chat',
    pinned: false,

    messages: [
      {
        sender: 'bot',

        text:
          "Namaste! 👋\nI’m BISNova — your guide to Indian Standards.\n\nAsk me anything about standards, certification, testing, licensing, hallmarking or any other BIS related services.",

        time: 'Now'
      }
    ]
  }
];


// ============================================================================
// APP
// ============================================================================

export default function App() {

  /*
   * Available views:
   *
   * landing  → Main BISNova website
   * faq      → FAQ page
   * chatbot  → BISNova chatbot
   */

  const [viewMode, setViewMode] = useState('landing');


  // ========================================================================
  // CHAT STATE
  // ========================================================================

  const [chats, setChats] = useState(
    INITIAL_CHATS
  );

  const [activeChatId, setActiveChatId] =
    useState('1');

  const [isThinking, setIsThinking] =
    useState(false);

  const [isTyping, setIsTyping] =
    useState(false);

  const [isSmiling, setIsSmiling] =
    useState(false);

  const [activeNav, setActiveNav] =
    useState('new-chat');

  const [isSidebarOpen, setIsSidebarOpen] =
    useState(true);


  // ========================================================================
  // MASCOT STATE
  // ========================================================================

  let mascotState = 'idle';

  if (isSmiling) {
    mascotState = 'smiling';
  }
  else if (isThinking) {
    mascotState = 'thinking';
  }
  else if (isTyping) {
    mascotState = 'reading';
  }


  // ========================================================================
  // ACTIVE CHAT
  // ========================================================================

  const activeChat =
    chats.find(
      chat => chat.id === activeChatId
    ) || chats[0];


  // ========================================================================
  // SIDEBAR TOGGLE
  // ========================================================================

  function handleToggleSidebar() {
    setIsSidebarOpen(
      previous => !previous
    );
  }


  // ========================================================================
  // BUILD BOT MESSAGE
  // ========================================================================

  function buildBotMessageFromResponse(
    apiResponse
  ) {

    const standardCards =
      (apiResponse.standards || []).map(
        std => ({
          code: std.is_number,
          title: std.title,
          mandatory: std.is_mandatory,
          relationship_type:
            std.relationship_type
        })
      );


    const actionChips =
      apiResponse.needs_clarification
        ? (
            apiResponse.clarification_options ||
            []
          ).map(opt => ({
            label: opt.label,
            icon: '❓',
            query: opt.query
          }))
        : null;


    const text =
      apiResponse.needs_clarification
        ? apiResponse.clarification_question
        : apiResponse.answer;


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

      time:
        new Date().toLocaleTimeString(
          [],
          {
            hour: '2-digit',
            minute: '2-digit'
          }
        ),

      isNew: true
    };
  }


  // ========================================================================
  // SEND MESSAGE
  // ========================================================================

  async function handleSendMessage(
    text,
    file = null
  ) {

    if (!text && !file) {
      return;
    }


    const currentTime =
      new Date().toLocaleTimeString(
        [],
        {
          hour: '2-digit',
          minute: '2-digit'
        }
      );


    // ----------------------------------------------------------------------
    // USER MESSAGE
    // ----------------------------------------------------------------------

    const userMsg = {

      sender: 'user',

      text:
        text ||
        `Attached file: ${file.name}`,

      file:
        file
          ? {
              name: file.name
            }
          : null,

      time: currentTime,

      isNew: true
    };


    setChats(prevChats =>

      prevChats.map(chat =>

        chat.id === activeChatId

          ? {
              ...chat,

              messages: [
                ...chat.messages,
                userMsg
              ]
            }

          : chat
      )
    );


    // ----------------------------------------------------------------------
    // THINKING
    // ----------------------------------------------------------------------

    setIsThinking(true);
    setIsTyping(false);


    // ----------------------------------------------------------------------
    // FILES CURRENTLY NOT SENT TO BACKEND
    // ----------------------------------------------------------------------

    if (!text) {

      setIsThinking(false);

      return;
    }


    // ----------------------------------------------------------------------
    // BACKEND REQUEST
    // ----------------------------------------------------------------------

    try {

      const apiResponse =
        await sendChatMessage(text);


      const botMsg =
        buildBotMessageFromResponse(
          apiResponse
        );


      setIsThinking(false);
      setIsSmiling(true);


      setChats(prevChats =>

        prevChats.map(chat =>

          chat.id === activeChatId

            ? {
                ...chat,

                messages: [
                  ...chat.messages,
                  botMsg
                ]
              }

            : chat
        )
      );


      setTimeout(() => {
        setIsSmiling(false);
      }, 1200);


    }
    catch (err) {

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
              minute: '2-digit'
            }
          ),

        isNew: true
      };


      setChats(prevChats =>

        prevChats.map(chat =>

          chat.id === activeChatId

            ? {
                ...chat,

                messages: [
                  ...chat.messages,
                  errorMsg
                ]
              }

            : chat
        )
      );
    }
  }


  // ========================================================================
  // OPEN CHATBOT WITH QUERY
  // ========================================================================

  function handleOpenChatbotWithQuery(
    query
  ) {

    setViewMode('chatbot');


    setTimeout(() => {

      handleSendMessage(query);

    }, 200);
  }


  // ========================================================================
  // NEW CHAT
  // ========================================================================

  function handleNewChat() {

    const newId =
      String(Date.now());


    const newChatSession = {

      id: newId,

      title: 'New Chat',

      pinned: false,

      messages: [
        {
          sender: 'bot',

          text:
            "Namaste! 👋\nI’m BISNova — your guide to Indian Standards.\nAsk me anything about standards, certification, testing, or licensing.",

          time:
            new Date().toLocaleTimeString(
              [],
              {
                hour: '2-digit',
                minute: '2-digit'
              }
            )
        }
      ]
    };


    setChats(prev => [
      newChatSession,
      ...prev
    ]);


    setActiveChatId(newId);

    setActiveNav('new-chat');
  }


  // ========================================================================
  // CLEAR CHAT
  // ========================================================================

  function handleClearChat() {

    if (
      confirm(
        'Clear messages in this conversation?'
      )
    ) {

      setChats(prev =>

        prev.map(chat =>

          chat.id === activeChatId

            ? {
                ...chat,

                messages: [
                  {
                    sender: 'bot',

                    text:
                      'Conversation cleared. Ask me anything about Indian Standards, testing, or BIS certification!',

                    time:
                      new Date().toLocaleTimeString(
                        [],
                        {
                          hour: '2-digit',
                          minute: '2-digit'
                        }
                      )
                  }
                ]
              }

            : chat
        )
      );
    }
  }


  // ========================================================================
  // PIN CHAT
  // ========================================================================

  function handlePinChat(chatId) {

    setChats(prev =>

      prev.map(chat =>

        chat.id === chatId

          ? {
              ...chat,
              pinned: !chat.pinned
            }

          : chat
      )
    );
  }


  // ========================================================================
  // RENAME CHAT
  // ========================================================================

  function handleRenameChat(
    chatId,
    newTitle
  ) {

    setChats(prev =>

      prev.map(chat =>

        chat.id === chatId

          ? {
              ...chat,
              title: newTitle
            }

          : chat
      )
    );
  }


  // ========================================================================
  // DELETE CHAT
  // ========================================================================

  function handleDeleteChat(chatId) {

    setChats(prev => {

      const filtered =
        prev.filter(
          chat => chat.id !== chatId
        );


      if (filtered.length === 0) {

        return [
          {
            id: '1',

            title: 'New Chat',

            pinned: false,

            messages: [
              {
                sender: 'bot',

                text:
                  "Namaste! 👋\nI’m BISNova — your guide to Indian Standards.",

                time: 'Now'
              }
            ]
          }
        ];
      }


      return filtered;
    });


    if (activeChatId === chatId) {

      const remaining =
        chats.filter(
          chat => chat.id !== chatId
        );


      setActiveChatId(
        remaining.length > 0
          ? remaining[0].id
          : '1'
      );
    }
  }


  // ========================================================================
  // SELECT CHAT
  // ========================================================================

  function handleSelectChat(chatId) {

    setActiveChatId(chatId);
  }


  // ========================================================================
  // CHAT SIDEBAR NAVIGATION
  // ========================================================================

  function handleNavClick(name) {

    setActiveNav(name);


    // FAQ
    if (
      name === 'Other Queries / FAQs'
    ) {

      setViewMode('faq');

      return;
    }


    // Explore Standards
    if (
      name === 'Explore Standards'
    ) {

      handleOpenChatbotWithQuery(
        'Show popular Indian Standards'
      );

      return;
    }


    // Testing and Labs
    if (
      name === 'Testing and Labs'
    ) {

      handleOpenChatbotWithQuery(
        'Where can I get my product tested?'
      );

      return;
    }


    // Dashboard
    if (
      name === 'Dashboard'
    ) {

      handleNewChat();

      return;
    }


    // Generic sidebar option
    handleOpenChatbotWithQuery(
      `Tell me about ${name}`
    );
  }


  // ========================================================================
  // MASCOT
  // ========================================================================

  function handleMascotClick() {

    setIsSmiling(true);


    setTimeout(() => {

      setIsSmiling(false);

    }, 1200);
  }


  // ========================================================================
  // MAIN NAVBAR NAVIGATION
  // ========================================================================
  //
  // IMPORTANT:
  //
  // Home and FAQ are separate APP VIEWS.
  //
  // Therefore we MUST change viewMode first.
  //
  // We should NOT attempt to find #hero while FAQ is mounted,
  // because the landing page does not exist in the DOM at that moment.
  //
  // ========================================================================

  function handleNavigateSection(
    destination
  ) {

    // ==========================================================
    // HOME
    // ==========================================================

    if (
      destination === 'home' ||
      destination === 'hero' ||
      destination === 'home-page'
    ) {

      // Switch back to landing page.
      setViewMode('landing');


      // Wait until React mounts the landing page.
      setTimeout(() => {

        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });

      }, 100);


      return;
    }


    // ==========================================================
    // FAQ
    // ==========================================================

    if (
      destination === 'faq' ||
      destination === 'faq-page'
    ) {

      // Switch to FAQ page.
      setViewMode('faq');


      // Start FAQ at the top.
      setTimeout(() => {

        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });

      }, 50);


      return;
    }


    // ==========================================================
    // STANDARDS
    // ==========================================================

    if (
      destination === 'standards' ||
      destination === 'how-bisnova-helps'
    ) {

      // First mount landing page.
      setViewMode('landing');


      // Then locate the Standards section.
      setTimeout(() => {

        const standardsSection =
          document.getElementById(
            'how-bisnova-helps'
          );


        if (standardsSection) {

          standardsSection.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });

        }
        else {

          console.warn(
            'BISNova: Could not find #how-bisnova-helps'
          );

        }

      }, 100);


      return;
    }


    // ==========================================================
    // FALLBACK
    // ==========================================================

    setViewMode('landing');


    setTimeout(() => {

      const element =
        document.getElementById(
          destination
        );


      if (element) {

        element.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });

      }

    }, 100);
  }


  // ==========================================================================
  // FAQ VIEW
  // ==========================================================================

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

          activeSection="faq"
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
        />

      </div>

    );
  }


  // ==========================================================================
  // LANDING VIEW
  // ==========================================================================

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

          activeSection="home"
        />


        <main className="landing-main-content">

          {/* ================================================================
              HERO
              ================================================================ */}

          <HeroSection

            onOpenChatbot={() =>
              setViewMode('chatbot')
            }

            onExploreStandards={() =>
              handleOpenChatbotWithQuery(
                'Show popular Indian Standards'
              )
            }

          />


          {/* ================================================================
              HOW BISNOVA HELPS
              ================================================================ */}

          <HowBisNovaHelps

            onOpenChatbotWithQuery={
              handleOpenChatbotWithQuery
            }

          />


          {/* ================================================================
              STANDARDS AND LABS
              ================================================================ */}

          <StandardsAndLabs

            onOpenChatbotWithQuery={
              handleOpenChatbotWithQuery
            }

          />


          {/* ================================================================
              CTA
              ================================================================ */}

          <CtaBanner

            onOpenChatbot={() =>
              setViewMode('chatbot')
            }

          />

        </main>


        {/* ================================================================
            FOOTER
            ================================================================ */}

        <Footer
          onOpenChatbot={() =>
            setViewMode('chatbot')
          }
        />

      </div>

    );
  }


  // ==========================================================================
  // CHATBOT VIEW
  // ==========================================================================

  return (

    <div className="app-container">

      {/* ====================================================================
          MOBILE SIDEBAR OVERLAY
          ==================================================================== */}

      {isSidebarOpen && (

        <div
          className="sidebar-overlay active"

          onClick={() =>
            setIsSidebarOpen(false)
          }
        />

      )}


      {/* ====================================================================
          SIDEBAR
          ==================================================================== */}

      <Sidebar

        isOpen={isSidebarOpen}

        onToggle={
          handleToggleSidebar
        }

        onCloseMobile={() =>
          setIsSidebarOpen(false)
        }

        chats={chats}

        activeChatId={
          activeChatId
        }

        onSelectChat={
          handleSelectChat
        }

        onNewChat={
          handleNewChat
        }

        onPinChat={
          handlePinChat
        }

        onRenameChat={
          handleRenameChat
        }

        onDeleteChat={
          handleDeleteChat
        }

        onNavClick={
          handleNavClick
        }

        activeNav={
          activeNav
        }

        mascotState={
          mascotState
        }

        onMascotClick={
          handleMascotClick
        }

      />


      {/* ====================================================================
          CHAT MAIN
          ==================================================================== */}

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


        {/* ==================================================================
            MESSAGES
            ================================================================== */}

        <MessageList

          messages={
            activeChat
              ? activeChat.messages
              : []
          }

          isThinking={
            isThinking
          }

          onChipClick={
            query =>
              handleSendMessage(query)
          }

        />


        {/* ==================================================================
            CHAT INPUT
            ================================================================== */}

        <ChatInput

          onSendMessage={
            handleSendMessage
          }

          onTypingChange={
            typing =>
              setIsTyping(typing)
          }

          onSelectSuggestion={
            query =>
              handleSendMessage(query)
          }

        />

      </main>

    </div>

  );
}