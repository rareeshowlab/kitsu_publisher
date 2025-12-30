<script lang="ts">
    let { isOpen = $bindable(false) } = $props();
    import { onMount } from "svelte";
    import logo from "$lib/assets/logo.png";

    let currentVersion = $state("");

    function close() {
        isOpen = false;
    }

    function openUrl(url: string) {
        if (
            window.pywebview &&
            window.pywebview.api &&
            window.pywebview.api.open_url
        ) {
            window.pywebview.api.open_url(url);
        } else {
            // 브라우저 환경인 경우
            window.open(url, "_blank");
        }
    }

    onMount(async () => {
        try {
            const res = await fetch("/system/check-update");
            const data = await res.json();
            currentVersion = data.current_version;
        } catch (e) {
            console.error("Failed to fetch version", e);
        }
    });
</script>

{#if isOpen}
    <div
        class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md animate-in fade-in duration-300"
        onclick={close}
        role="button"
        tabindex="-1"
        onkeydown={(e) => e.key === "Escape" && close()}
    >
        <div
            class="bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl max-w-sm w-full p-8 relative overflow-hidden animate-in zoom-in-95 duration-300"
            onclick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
        >
            <!-- Decorative Background -->
            <div
                class="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/10 rounded-full blur-3xl"
            ></div>
            <div
                class="absolute -bottom-24 -left-24 w-48 h-48 bg-purple-600/10 rounded-full blur-3xl"
            ></div>

            <button
                onclick={close}
                class="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
                aria-label="Close modal"
            >
                <svg
                    class="w-6 h-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"
                    />
                </svg>
            </button>

            <div class="text-center">
                <div class="relative w-20 h-20 mx-auto mb-6 group">
                    <div
                        class="absolute inset-0 bg-blue-600/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"
                    ></div>
                    <img
                        src={logo}
                        alt="Logo"
                        class="w-full h-full object-contain relative z-10 drop-shadow-lg"
                    />
                </div>

                <h2 class="text-2xl font-bold text-white mb-1">
                    Kitsu Publisher
                </h2>
                {#if currentVersion}
                    <p class="text-blue-500 font-mono text-xs mb-2">
                        v{currentVersion}
                    </p>
                {/if}
                <p class="text-slate-400 text-sm mb-6">
                    Efficient batch upload tool for Kitsu
                </p>

                <div class="space-y-4">
                    <div
                        class="p-4 bg-slate-800/50 rounded-2xl border border-slate-700/50"
                    >
                        <h3
                            class="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2"
                        >
                            Developed by
                        </h3>
                        <p class="text-white font-semibold">Raree-show Lab</p>
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <button
                            onclick={() =>
                                openUrl("https://www.rareeshowlab.com")}
                            class="flex flex-col items-center gap-2 p-3 bg-slate-800/30 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all group"
                        >
                            <svg
                                class="w-5 h-5 text-blue-400 group-hover:scale-110 transition-transform"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                                />
                            </svg>
                            <span
                                class="text-[10px] font-bold text-slate-400 uppercase tracking-wider"
                                >Website</span
                            >
                        </button>
                        <button
                            onclick={() =>
                                openUrl(
                                    "https://github.com/rareeshowlab/kitsu_publisher",
                                )}
                            class="flex flex-col items-center gap-2 p-3 bg-slate-800/30 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all group"
                        >
                            <svg
                                class="w-5 h-5 text-slate-300 group-hover:scale-110 transition-transform"
                                fill="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                                />
                            </svg>
                            <span
                                class="text-[10px] font-bold text-slate-400 uppercase tracking-wider"
                                >GitHub</span
                            >
                        </button>
                    </div>
                </div>

                <p class="text-slate-600 text-[10px] mt-8 font-medium">
                    © 2025 Raree-show Lab. All rights reserved.
                </p>
            </div>
        </div>
    </div>
{/if}
