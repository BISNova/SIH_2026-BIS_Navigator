import React, { useEffect, useMemo, useState } from 'react';
import {
    fetchCatalogLabs,
    fetchHallmarkingCentres,
    BISNovaAPIError,
} from '../api';

export default function TestingLabsPage({ onOpenChatbot }) {
    const [activeTab, setActiveTab] = useState('labs');

    // -----------------------------
    // Laboratory data
    // -----------------------------
    const [labs, setLabs] = useState([]);
    const [labsLoading, setLabsLoading] = useState(true);
    const [labsError, setLabsError] = useState(null);

    // -----------------------------
    // Hallmarking data
    // -----------------------------
    const [centres, setCentres] = useState([]);
    const [centresLoading, setCentresLoading] = useState(false);
    const [centresError, setCentresError] = useState(null);

    // -----------------------------
    // Common filters
    // -----------------------------
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedState, setSelectedState] = useState('All States');
    const [selectedCity, setSelectedCity] = useState('All Cities');

    // Laboratory-specific filter
    const [selectedLabType, setSelectedLabType] = useState('All Types');
    const [selectedLabStatus, setSelectedLabStatus] = useState('All Status');

    // Hallmarking-specific filter
    const [selectedRecognitionStatus, setSelectedRecognitionStatus] =
        useState('All Status');

    // =========================================================
    // LOAD LABORATORIES
    // =========================================================

    useEffect(() => {
        let cancelled = false;

        setLabsLoading(true);

        fetchCatalogLabs()
            .then(data => {
                if (cancelled) return;

                setLabs(Array.isArray(data) ? data : []);
                setLabsLoading(false);
            })
            .catch(err => {
                if (cancelled) return;

                setLabsError(
                    err instanceof BISNovaAPIError
                        ? err.message
                        : 'Something went wrong loading testing laboratories.'
                );

                setLabsLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    // =========================================================
    // LOAD HALLMARKING CENTRES WHEN TAB IS OPENED
    // =========================================================

    useEffect(() => {
        if (activeTab !== 'hallmarking' || centres.length > 0) {
            return;
        }

        let cancelled = false;

        setCentresLoading(true);
        setCentresError(null);

        fetchHallmarkingCentres()
            .then(data => {
                if (cancelled) return;

                setCentres(Array.isArray(data) ? data : []);
                setCentresLoading(false);
            })
            .catch(err => {
                if (cancelled) return;

                setCentresError(
                    err instanceof BISNovaAPIError
                        ? err.message
                        : 'Something went wrong loading assaying and hallmarking centres.'
                );

                setCentresLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [activeTab, centres.length]);

    // =========================================================
    // LAB FILTER OPTIONS
    // =========================================================

    const labTypes = useMemo(() => {
        const values = new Set(
            labs
                .map(lab => lab.lab_type)
                .filter(Boolean)
        );

        return ['All Types', ...Array.from(values).sort()];
    }, [labs]);

    const labStatuses = useMemo(() => {
        const values = new Set(
            labs
                .map(lab => lab.status)
                .filter(Boolean)
        );

        return ['All Status', ...Array.from(values).sort()];
    }, [labs]);

    // =========================================================
    // LOCATION OPTIONS
    // =========================================================

    const sourceData =
        activeTab === 'labs' ? labs : centres;

    const states = useMemo(() => {
        const values = new Set(
            sourceData
                .map(item => item.state)
                .filter(Boolean)
        );

        return ['All States', ...Array.from(values).sort()];
    }, [sourceData]);

    const cities = useMemo(() => {
        const values = new Set(
            sourceData
                .filter(item =>
                    selectedState === 'All States' ||
                    item.state === selectedState
                )
                .map(item => item.city)
                .filter(Boolean)
        );

        return ['All Cities', ...Array.from(values).sort()];
    }, [sourceData, selectedState]);

    // =========================================================
    // FILTER LABORATORIES
    // =========================================================

    const filteredLabs = useMemo(() => {
        const term = searchTerm.trim().toLowerCase();

        return labs.filter(lab => {
            const matchesSearch =
                !term ||
                [
                    lab.lab_name,
                    lab.lab_type,
                    lab.city,
                    lab.district,
                    lab.state,
                    lab.contact,
                ]
                    .filter(Boolean)
                    .some(value =>
                        String(value).toLowerCase().includes(term)
                    );

            const matchesType =
                selectedLabType === 'All Types' ||
                lab.lab_type === selectedLabType;

            const matchesStatus =
                selectedLabStatus === 'All Status' ||
                lab.status === selectedLabStatus;

            const matchesState =
                selectedState === 'All States' ||
                lab.state === selectedState;

            const matchesCity =
                selectedCity === 'All Cities' ||
                lab.city === selectedCity;

            return (
                matchesSearch &&
                matchesType &&
                matchesStatus &&
                matchesState &&
                matchesCity
            );
        });
    }, [
        labs,
        searchTerm,
        selectedLabType,
        selectedLabStatus,
        selectedState,
        selectedCity,
    ]);

    // =========================================================
    // FILTER HALLMARKING CENTRES
    // =========================================================

    const filteredCentres = useMemo(() => {
        const term = searchTerm.trim().toLowerCase();

        return centres.filter(centre => {
            const matchesSearch =
                !term ||
                [
                    centre.centre_name,
                    centre.recognition_number,
                    centre.centre_type,
                    centre.city,
                    centre.district,
                    centre.state,
                    centre.contact,
                    centre.phone,
                ]
                    .filter(Boolean)
                    .some(value =>
                        String(value).toLowerCase().includes(term)
                    );

            const matchesStatus =
                selectedRecognitionStatus === 'All Status' ||
                centre.recognition_status === selectedRecognitionStatus;

            const matchesState =
                selectedState === 'All States' ||
                centre.state === selectedState;

            const matchesCity =
                selectedCity === 'All Cities' ||
                centre.city === selectedCity;

            return (
                matchesSearch &&
                matchesStatus &&
                matchesState &&
                matchesCity
            );
        });
    }, [
        centres,
        searchTerm,
        selectedRecognitionStatus,
        selectedState,
        selectedCity,
    ]);

    // =========================================================
    // RESET LOCATION WHEN STATE CHANGES
    // =========================================================

    function handleStateChange(value) {
        setSelectedState(value);
        setSelectedCity('All Cities');
    }

    // =========================================================
    // SWITCH TABS
    // =========================================================

    function handleTabChange(tab) {
        setActiveTab(tab);

        setSearchTerm('');
        setSelectedState('All States');
        setSelectedCity('All Cities');

        if (tab === 'labs') {
            setSelectedLabType('All Types');
            setSelectedLabStatus('All Status');
        } else {
            setSelectedRecognitionStatus('All Status');
        }
    }

    return (
        <div className="testing-labs-page">

            {/* =====================================================
          HERO
      ===================================================== */}

            <section className="testing-labs-hero">
                <h1 className="testing-labs-hero-title">
                    Testing &amp; Labs
                </h1>

                <p className="testing-labs-hero-description">
                    Find BIS testing laboratories and Assaying &amp;
                    Hallmarking Centres for your product and
                    certification needs.
                </p>
            </section>

            <main className="testing-labs-content">

                {/* ===================================================
            MAIN TABS
        =================================================== */}

                <div className="testing-labs-tabs">

                    <button
                        type="button"
                        className={`testing-labs-tab ${activeTab === 'labs' ? 'active' : ''
                            }`}
                        onClick={() => handleTabChange('labs')}
                    >
                        Testing Laboratories
                    </button>

                    <button
                        type="button"
                        className={`testing-labs-tab ${activeTab === 'hallmarking' ? 'active' : ''
                            }`}
                        onClick={() => handleTabChange('hallmarking')}
                    >
                        Assaying &amp; Hallmarking
                    </button>

                </div>

                {/* ===================================================
            SEARCH
        =================================================== */}

                <div className="testing-labs-search-wrapper">

                    <svg
                        className="testing-labs-search-icon"
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                    >
                        <circle
                            cx="11"
                            cy="11"
                            r="7"
                            stroke="currentColor"
                            strokeWidth="2"
                        />
                        <line
                            x1="21"
                            y1="21"
                            x2="16.65"
                            y2="16.65"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                        />
                    </svg>

                    <input
                        type="text"
                        className="testing-labs-search-input"
                        placeholder={
                            activeTab === 'labs'
                                ? 'Search laboratories by name, city, district, or state...'
                                : 'Search centres by name, recognition number, city, or state...'
                        }
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />

                    {searchTerm && (
                        <button
                            type="button"
                            className="testing-labs-clear-search"
                            onClick={() => setSearchTerm('')}
                        >
                            ✕
                        </button>
                    )}

                </div>

                {/* ===================================================
            FILTERS
        =================================================== */}

                <div className="testing-labs-filter-section">

                    <div className="testing-labs-filter-row">

                        {/* LAB TYPE */}
                        {activeTab === 'labs' && (
                            <>
                                <div className="testing-labs-filter-group">
                                    <span className="testing-labs-filter-label">
                                        Laboratory Type
                                    </span>

                                    <div className="testing-labs-pills">
                                        {labTypes.map(type => (
                                            <button
                                                key={type}
                                                type="button"
                                                className={`testing-labs-pill ${selectedLabType === type
                                                    ? 'active'
                                                    : ''
                                                    }`}
                                                onClick={() =>
                                                    setSelectedLabType(type)
                                                }
                                            >
                                                {type}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* STATUS */}
                                {labStatuses.length > 1 && (
                                    <div className="testing-labs-filter-group">
                                        <span className="testing-labs-filter-label">
                                            Status
                                        </span>

                                        <div className="testing-labs-pills">
                                            {labStatuses.map(status => (
                                                <button
                                                    key={status}
                                                    type="button"
                                                    className={`testing-labs-pill ${selectedLabStatus === status
                                                        ? 'active'
                                                        : ''
                                                        }`}
                                                    onClick={() =>
                                                        setSelectedLabStatus(status)
                                                    }
                                                >
                                                    {status}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        {/* HALLMARKING STATUS */}
                        {activeTab === 'hallmarking' && (
                            <div className="testing-labs-filter-group">
                                <span className="testing-labs-filter-label">
                                    Recognition Status
                                </span>

                                <div className="testing-labs-pills">
                                    {[
                                        'All Status',
                                        ...Array.from(
                                            new Set(
                                                centres
                                                    .map(c => c.recognition_status)
                                                    .filter(Boolean)
                                            )
                                        ).sort(),
                                    ].map(status => (
                                        <button
                                            key={status}
                                            type="button"
                                            className={`testing-labs-pill ${selectedRecognitionStatus === status
                                                ? 'active'
                                                : ''
                                                }`}
                                            onClick={() =>
                                                setSelectedRecognitionStatus(status)
                                            }
                                        >
                                            {status}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                    </div>

                    {/* LOCATION */}
                    <div className="testing-labs-location-filters">

                        <span className="testing-labs-filter-label">
                            Location
                        </span>

                        <select
                            className="testing-labs-select"
                            value={selectedState}
                            onChange={e =>
                                handleStateChange(e.target.value)
                            }
                        >
                            {states.map(state => (
                                <option key={state} value={state}>
                                    {state}
                                </option>
                            ))}
                        </select>

                        <select
                            className="testing-labs-select"
                            value={selectedCity}
                            onChange={e =>
                                setSelectedCity(e.target.value)
                            }
                        >
                            {cities.map(city => (
                                <option key={city} value={city}>
                                    {city}
                                </option>
                            ))}
                        </select>

                    </div>

                </div>

                {/* ===================================================
            TESTING LABS
        =================================================== */}

                {activeTab === 'labs' && (
                    <>
                        {labsLoading && (
                            <div className="testing-labs-state">
                                Loading testing laboratories…
                            </div>
                        )}

                        {labsError && (
                            <div className="testing-labs-state testing-labs-state-error">
                                {labsError}
                            </div>
                        )}

                        {!labsLoading &&
                            !labsError &&
                            filteredLabs.length === 0 && (
                                <div className="testing-labs-state">
                                    No testing laboratories match your filters.
                                </div>
                            )}

                        {!labsLoading &&
                            !labsError &&
                            filteredLabs.length > 0 && (
                                <div className="testing-labs-grid">

                                    {filteredLabs.map(lab => (
                                        <article
                                            key={lab.lab_id}
                                            className="testing-lab-card"
                                        >

                                            <div className="testing-lab-card-top">

                                                {lab.lab_type && (
                                                    <span className="testing-lab-type">
                                                        {lab.lab_type}
                                                    </span>
                                                )}

                                                {lab.status && (
                                                    <span
                                                        className={`testing-lab-status ${String(lab.status)
                                                            .toLowerCase()
                                                            .includes('recogn')
                                                            ? 'recognized'
                                                            : ''
                                                            }`}
                                                    >
                                                        {lab.status}
                                                    </span>
                                                )}

                                            </div>

                                            <h3>{lab.lab_name}</h3>

                                            {(lab.city ||
                                                lab.district ||
                                                lab.state) && (
                                                    <p className="testing-lab-location">
                                                        {[lab.city, lab.district, lab.state]
                                                            .filter(Boolean)
                                                            .join(', ')}
                                                    </p>
                                                )}

                                            {lab.address && (
                                                <p className="testing-lab-address">
                                                    {lab.address}
                                                </p>
                                            )}

                                            {lab.contact && (
                                                <p className="testing-lab-contact">
                                                    {lab.contact}
                                                </p>
                                            )}

                                            <div className="testing-lab-card-actions">

                                                <button
                                                    type="button"
                                                    className="testing-lab-scope-btn"
                                                >
                                                    View Testing Scope →
                                                </button>

                                                <button
                                                    type="button"
                                                    className="explore-card-ask-btn testing-lab-ask-btn"
                                                    onClick={() =>
                                                        onOpenChatbot(
                                                            `Tell me about ${lab.lab_name}, including its location, contact details and available testing facilities.`
                                                        )
                                                    }
                                                >
                                                    Ask BISNova →
                                                </button>

                                            </div>

                                        </article>
                                    ))}

                                </div>
                            )}
                    </>
                )}

                {/* ===================================================
            ASSAYING & HALLMARKING
        =================================================== */}

                {activeTab === 'hallmarking' && (
                    <>
                        {centresLoading && (
                            <div className="testing-labs-state">
                                Loading Assaying &amp; Hallmarking Centres…
                            </div>
                        )}

                        {centresError && (
                            <div className="testing-labs-state testing-labs-state-error">
                                {centresError}
                            </div>
                        )}

                        {!centresLoading &&
                            !centresError &&
                            filteredCentres.length === 0 && (
                                <div className="testing-labs-state">
                                    No Assaying &amp; Hallmarking Centres match
                                    your filters.
                                </div>
                            )}

                        {!centresLoading &&
                            !centresError &&
                            filteredCentres.length > 0 && (
                                <div className="testing-labs-grid">

                                    {filteredCentres.map(centre => (
                                        <article
                                            key={centre.ah_centre_id}
                                            className="testing-lab-card"
                                        >

                                            <div className="testing-lab-card-top">

                                                {centre.centre_type && (
                                                    <span className="testing-lab-type">
                                                        {centre.centre_type}
                                                    </span>
                                                )}

                                                {centre.recognition_status && (
                                                    <span className="testing-lab-status recognized">
                                                        {centre.recognition_status}
                                                    </span>
                                                )}

                                            </div>

                                            <h3>{centre.centre_name}</h3>

                                            {centre.recognition_number && (
                                                <p className="testing-lab-location">
                                                    Recognition No.{' '}
                                                    {centre.recognition_number}
                                                </p>
                                            )}

                                            {(centre.city ||
                                                centre.district ||
                                                centre.state) && (
                                                    <p className="testing-lab-address">
                                                        {[centre.city, centre.district, centre.state]
                                                            .filter(Boolean)
                                                            .join(', ')}
                                                    </p>
                                                )}

                                            {centre.address && (
                                                <p className="testing-lab-address">
                                                    {centre.address}
                                                </p>
                                            )}

                                            <div className="testing-lab-hallmarking">

                                                {centre.gold_hallmarking && (
                                                    <span className="testing-lab-hallmark-badge">
                                                        Gold Hallmarking
                                                    </span>
                                                )}

                                                {centre.silver_hallmarking && (
                                                    <span className="testing-lab-hallmark-badge">
                                                        Silver Hallmarking
                                                    </span>
                                                )}

                                            </div>

                                            {(centre.phone ||
                                                centre.email ||
                                                centre.contact) && (
                                                    <p className="testing-lab-contact">
                                                        {centre.phone ||
                                                            centre.contact ||
                                                            centre.email}
                                                    </p>
                                                )}

                                            <div className="testing-lab-card-actions">

                                                <button
                                                    type="button"
                                                    className="explore-card-ask-btn testing-lab-ask-btn"
                                                    onClick={() =>
                                                        onOpenChatbot(
                                                            `Tell me about ${centre.centre_name}, its BIS recognition, location and hallmarking services.`
                                                        )
                                                    }
                                                >
                                                    Ask BISNova
                                                </button>

                                                {centre.source_url && (
                                                    <a
                                                        href={centre.source_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="testing-lab-source-link"
                                                    >
                                                        Source
                                                    </a>
                                                )}

                                            </div>

                                        </article>
                                    ))}

                                </div>
                            )}

                    </>
                )}

            </main>
        </div>
    );
}