// abstract: Standalone taxonomy card-scope layout tuning interface.
// out_of_scope: Production app routing and taxonomy view data fetching.

import { RefreshCw, RotateCcw } from "lucide-react";
import {
  type Dispatch,
  type SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import { TaxonomyLayoutLabPreview } from "./TaxonomyLayoutLabPreview";
import {
  DEFAULT_LAYOUT_LAB_API_BASE_URL,
  fetchLayoutLabDefaultParams,
  fetchLayoutLabFixtures,
  type LayoutLabFixtureSummary,
  solveLayoutLab,
} from "./taxonomyLayoutLabApi";
import {
  TAXONOMY_LAYOUT_LAB_PARAM_DEFINITIONS,
  type TaxonomyLayoutLabParamKey,
  type TaxonomyLayoutLabParams,
} from "./taxonomyLayoutLabParams";

type LayoutLabStatus = "idle" | "loading" | "solving" | "ready" | "error";

export function TaxonomyLayoutLabApp() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_LAYOUT_LAB_API_BASE_URL);
  const [fixtures, setFixtures] = useState<LayoutLabFixtureSummary[]>([]);
  const [selectedFixtureName, setSelectedFixtureName] = useState("");
  const [defaultParams, setDefaultParams] =
    useState<TaxonomyLayoutLabParams | null>(null);
  const [params, setParams] = useState<Partial<TaxonomyLayoutLabParams>>({});
  const [layout, setLayout] =
    useState<TaxonomyCardScopeLayoutSliceResponse | null>(null);
  const [status, setStatus] = useState<LayoutLabStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedFixture = useMemo(
    () => fixtures.find((fixture) => fixture.name === selectedFixtureName),
    [fixtures, selectedFixtureName],
  );

  const loadLabData = useCallback(
    async (signal?: AbortSignal) => {
      setStatus("loading");
      setErrorMessage(null);
      const [fixtureData, parameterData] = await Promise.all([
        fetchLayoutLabFixtures({ apiBaseUrl, signal }),
        fetchLayoutLabDefaultParams({ apiBaseUrl, signal }),
      ]);

      setFixtures(fixtureData);
      setDefaultParams(parameterData);
      setParams(parameterData);
      setSelectedFixtureName((currentFixtureName) => {
        if (
          currentFixtureName &&
          fixtureData.some((fixture) => fixture.name === currentFixtureName)
        ) {
          return currentFixtureName;
        }

        return fixtureData[0]?.name ?? "";
      });
    },
    [apiBaseUrl],
  );

  useEffect(() => {
    const controller = new AbortController();

    loadLabData(controller.signal).catch((error: unknown) => {
      if (controller.signal.aborted) {
        return;
      }

      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : String(error));
    });

    return () => {
      controller.abort();
    };
  }, [loadLabData]);

  useEffect(() => {
    if (!selectedFixtureName || !defaultParams) {
      return;
    }

    const controller = new AbortController();
    const solveTimer = window.setTimeout(() => {
      setStatus("solving");
      setErrorMessage(null);
      solveLayoutLab({
        apiBaseUrl,
        fixtureName: selectedFixtureName,
        params,
        signal: controller.signal,
      })
        .then((nextLayout) => {
          setLayout(nextLayout);
          setStatus("ready");
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) {
            return;
          }

          setStatus("error");
          setErrorMessage(
            error instanceof Error ? error.message : String(error),
          );
        });
    }, 120);

    return () => {
      window.clearTimeout(solveTimer);
      controller.abort();
    };
  }, [apiBaseUrl, defaultParams, params, selectedFixtureName]);

  return (
    <main className="grid h-screen min-h-0 grid-cols-[390px_minmax(0,1fr)] bg-[#F8FAFC] text-[#0F172A]">
      <aside className="flex min-h-0 flex-col border-r border-[#D6E3F7] bg-white">
        <header className="border-b border-[#E2E8F0] px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="m-0 text-[18px] leading-6 font-semibold">
                Layout Lab
              </h1>
              <p className="m-0 mt-1 text-[12px] leading-4 text-[#64748B]">
                {selectedFixture
                  ? `${selectedFixture.node_count} nodes / ${selectedFixture.edge_count} edges`
                  : status}
              </p>
            </div>
            <button
              aria-label="Reload fixtures and defaults"
              className="grid size-9 place-items-center rounded-[8px] border border-[#CBD5E1] bg-white text-[#334155] hover:bg-[#F8FAFC]"
              onClick={() => {
                const controller = new AbortController();
                loadLabData(controller.signal).catch((error: unknown) => {
                  setStatus("error");
                  setErrorMessage(
                    error instanceof Error ? error.message : String(error),
                  );
                });
              }}
              type="button"
            >
              <RefreshCw aria-hidden="true" size={16} />
            </button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
          <label className="flex flex-col gap-2 text-[12px] font-medium text-[#475569]">
            API
            <input
              className="h-9 rounded-[8px] border border-[#CBD5E1] px-3 text-[13px] text-[#0F172A] outline-none focus:border-[#2563EB]"
              onChange={(event) => setApiBaseUrl(event.target.value)}
              value={apiBaseUrl}
            />
          </label>

          <label className="flex flex-col gap-2 text-[12px] font-medium text-[#475569]">
            Fixture
            <select
              className="h-9 rounded-[8px] border border-[#CBD5E1] bg-white px-3 text-[13px] text-[#0F172A] outline-none focus:border-[#2563EB]"
              onChange={(event) => setSelectedFixtureName(event.target.value)}
              value={selectedFixtureName}
            >
              {fixtures.map((fixture) => (
                <option key={fixture.name} value={fixture.name}>
                  {fixture.name}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center justify-between border-y border-[#E2E8F0] py-3">
            <span className="text-[12px] font-medium text-[#475569]">
              Parameters
            </span>
            <button
              className="inline-flex h-8 items-center gap-2 rounded-[8px] border border-[#CBD5E1] bg-white px-3 text-[12px] font-medium text-[#334155] hover:bg-[#F8FAFC]"
              disabled={!defaultParams}
              onClick={() => {
                if (defaultParams) {
                  setParams(defaultParams);
                }
              }}
              type="button"
            >
              <RotateCcw aria-hidden="true" size={14} />
              Reset
            </button>
          </div>

          <div className="flex flex-col gap-4">
            {TAXONOMY_LAYOUT_LAB_PARAM_DEFINITIONS.map((definition) => {
              const value = params[definition.key] ?? definition.min;

              return (
                <label
                  className="grid gap-2 text-[12px] text-[#475569]"
                  key={definition.key}
                >
                  <span className="flex items-center justify-between gap-3">
                    <span className="font-medium">{definition.label}</span>
                    <input
                      className="h-8 w-[96px] rounded-[8px] border border-[#CBD5E1] px-2 text-right text-[12px] text-[#0F172A] outline-none focus:border-[#2563EB]"
                      max={definition.max}
                      min={definition.min}
                      onChange={(event) =>
                        setParamValue(
                          setParams,
                          definition.key,
                          Number(event.target.value),
                        )
                      }
                      step={definition.step}
                      type="number"
                      value={formatParamValue(value, definition.step)}
                    />
                  </span>
                  <input
                    max={definition.max}
                    min={definition.min}
                    onChange={(event) =>
                      setParamValue(
                        setParams,
                        definition.key,
                        Number(event.target.value),
                      )
                    }
                    step={definition.step}
                    type="range"
                    value={value}
                  />
                </label>
              );
            })}
          </div>
        </div>
      </aside>

      <section className="relative min-h-0 overflow-hidden">
        <div className="absolute top-4 left-4 z-20 rounded-[8px] border border-[#D6E3F7] bg-white/90 px-3 py-2 text-[12px] text-[#475569] shadow-sm">
          {status === "solving" ? "Solving" : status}
          {errorMessage ? `: ${errorMessage}` : ""}
        </div>
        <TaxonomyLayoutLabPreview layout={layout} />
      </section>
    </main>
  );
}

function setParamValue(
  setParams: Dispatch<SetStateAction<Partial<TaxonomyLayoutLabParams>>>,
  key: TaxonomyLayoutLabParamKey,
  rawValue: number,
) {
  const value = key === "simulation_ticks" ? Math.round(rawValue) : rawValue;
  setParams((currentParams) => ({
    ...currentParams,
    [key]: value,
  }));
}

function formatParamValue(value: number, step: number): string {
  if (step >= 1) {
    return String(Math.round(value));
  }

  const fractionDigits = Math.max(0, Math.ceil(-Math.log10(step)));
  return value.toFixed(fractionDigits);
}
