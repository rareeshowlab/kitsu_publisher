<script lang="ts">
	import { user, kitsuHost } from "$lib/store";
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import logo from "$lib/assets/logo.png";
	import AboutModal from "$lib/components/AboutModal.svelte";

	// State
	let aboutOpen = $state(false);
	let projects = $state([]);
	let selectedProjectId = $state("");
	let statusTypes = $state([]);
	let globalStatusId = $state("");

	let directoryPath = $state("");
	let displayGroups = $state<any[]>([]); // UI에 표시될 그룹화된 데이터

	let loading = $state(false);
	let matching = $state(false); // 매칭 진행 중 여부
	let publishing = $state(false);
	let error = $state("");
	let checkingSession = $state(true);

	// UI State
	let showSuccessModal = $state(false);
	let publishResults = $state({ success: 0, failed: 0 });
	let sortConfig = $state({ key: "priority", direction: "asc" });

	// Update State
	let updateInfo = $state(null);

	// Log Viewer State
	let showLogs = $state(false);
	let logs = $state([]);
	let logContainer = $state(null);

	function toggleLogs() {
		showLogs = !showLogs;
		if (showLogs) {
			setTimeout(() => {
				if (logContainer)
					logContainer.scrollTop = logContainer.scrollHeight;
			}, 100);
		}
	}

	function appendLog(message) {
		logs.push(message);
		if (logs.length > 500) logs.shift(); // 최대 500줄 유지
		// 새 로그가 오면 자동 스크롤
		if (showLogs && logContainer) {
			requestAnimationFrame(() => {
				logContainer.scrollTop = logContainer.scrollHeight;
			});
		}
	}

	// 정렬된 그룹 데이터 (Derived)
	let sortedGroups = $derived.by(() => {
		let items = [...displayGroups];

		items.sort((a, b) => {
			let result = 0;

			if (sortConfig.key === "priority") {
				// 1. 선택된 것(퍼블리쉬 대상) 우선
				if (a.selected !== b.selected) return a.selected ? -1 : 1;
				// 2. 이미 퍼블리쉬 된 것은 뒤로
				if (a.is_published !== b.is_published)
					return a.is_published ? 1 : -1;
				// 3. 매치 상태 우선순위
				const statusOrder = { full: 0, shot_only: 1, none: 2 };
				if (a.match_status !== b.match_status) {
					result =
						statusOrder[a.match_status] -
						statusOrder[b.match_status];
				}
			} else if (sortConfig.key === "shot_name") {
				result = (a.shot_name || "").localeCompare(b.shot_name || "");
			} else if (sortConfig.key === "filename") {
				result = a.filename.localeCompare(b.filename);
			} else if (sortConfig.key === "version") {
				result = (a.version || 0) - (b.version || 0);
			}

			// 결과가 0이면 이름으로 2차 정렬
			if (result === 0) {
				const nameA = a.shot_name || a.filename;
				const nameB = b.shot_name || b.filename;
				result = nameA.localeCompare(nameB);
			}

			return sortConfig.direction === "asc" ? result : -result;
		});

		return items;
	});

	function toggleSort(key) {
		if (sortConfig.key === key) {
			sortConfig.direction =
				sortConfig.direction === "asc" ? "desc" : "asc";
		} else {
			sortConfig.key = key;
			sortConfig.direction = "asc";
		}
	}

	// 일괄 설정을 위한 전체 태스크 타입 목록 추출
	let uniqueTaskTypes = $derived.by(() => {
		const tasks = new Set();
		displayGroups.forEach((g) => {
			g.available_tasks.forEach((t) => tasks.add(t.name));
		});
		return Array.from(tasks).sort();
	});

	onMount(async () => {
		// Log Streaming 시작
		const evtSource = new EventSource("/logs/stream");
		evtSource.onmessage = (event) => {
			appendLog(event.data);
		};

		let storedTokens = localStorage.getItem("kitsu_tokens");
		let storedHost = localStorage.getItem("kitsu_host");
		let lastDir = localStorage.getItem("last_directory");

		// 1. 데스크탑 앱 환경인 경우 백엔드에서 세션/설정 가져오기
		if (window.pywebview && window.pywebview.api) {
			try {
				if (window.pywebview.api.get_session) {
					const session = await window.pywebview.api.get_session();
					if (session) {
						storedTokens = JSON.stringify(session.tokens);
						storedHost = session.host;
					}
				}
				if (window.pywebview.api.get_setting) {
					const path =
						await window.pywebview.api.get_setting(
							"last_directory",
						);
					if (path) lastDir = path;
				}
			} catch (e) {
				console.error("Failed to get data from backend", e);
			}
		}

		// Check for updates
		fetch("/system/check-update")
			.then((res) => res.json())
			.then((data) => {
				if (data.update_available) {
					updateInfo = data;
					appendLog(`Update available: v${data.latest_version}`);
				}
			})
			.catch((err) => console.error("Update check failed", err));

		if (!$user && storedTokens && storedHost) {
			try {
				const response = await fetch("/auth/restore-session", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						host: storedHost,
						tokens: JSON.parse(storedTokens),
					}),
				});
				if (response.ok) {
					const data = await response.json();
					user.set(data.user);
					kitsuHost.set(storedHost);
				} else {
					if (
						window.pywebview &&
						window.pywebview.api &&
						window.pywebview.api.clear_session
					) {
						await window.pywebview.api.clear_session();
					}
					localStorage.removeItem("kitsu_tokens");
					goto("/");
				}
			} catch (e) {
				goto("/");
			}
		} else if (!$user) {
			goto("/");
		}
		checkingSession = false;

		if ($user) {
			await Promise.all([fetchProjects(), fetchStatusTypes()]);
			if (lastDir) directoryPath = lastDir;
		}
	});

	async function fetchProjects() {
		try {
			const res = await fetch("/kitsu/projects");
			if (res.ok) projects = await res.json();
		} catch (e) {
			console.error(e);
		}
	}

	async function fetchStatusTypes() {
		try {
			const res = await fetch("/kitsu/task-status-types");
			if (res.ok) {
				statusTypes = await res.json();
				if (statusTypes.length > 0) {
					const rev = statusTypes.find(
						(s) => s.short_name.toUpperCase() === "REV",
					);
					const fallback = statusTypes.find((s) =>
						["review", "wfa", "pending"].includes(
							s.short_name.toLowerCase(),
						),
					);
					globalStatusId = rev
						? rev.id
						: fallback
							? fallback.id
							: statusTypes[0].id;
				}
			}
		} catch (e) {
			console.error(e);
		}
	}

	async function scanDirectory() {
		if (!selectedProjectId || !directoryPath) {
			error = "Please select a project and enter a directory path.";
			return;
		}
		if (
			window.pywebview &&
			window.pywebview.api &&
			window.pywebview.api.save_setting
		) {
			await window.pywebview.api.save_setting(
				"last_directory",
				directoryPath,
			);
		}
		localStorage.setItem("last_directory", directoryPath);
		loading = true;
		error = "";
		displayGroups = [];

		try {
			const response = await fetch("/files/scan", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					directory: directoryPath,
					project_id: selectedProjectId,
				}),
			});
			if (response.ok) {
				const data = await response.json();
				if (data.length === 0) {
					error = "No video files found.";
				} else {
					// 1. 우선 파일들을 그룹화하여 화면에 즉시 표시 (Match 정보 없이)
					const groups = {};
					data.forEach((file) => {
						// 샷+태스크 정보가 파싱되었으므로 이를 기준으로 임시 그룹화
						const groupKey = file.shot_name
							? `${file.shot_name}_${file.task_name}`
							: `unmatched_${file.filename}`;
						if (!groups[groupKey]) {
							groups[groupKey] = {
								...file,
								all_versions: [],
								selected_file_index: 0,
								selected: false,
								comment: "",
								status_id: globalStatusId,
								// 매칭 정보 초기화
								shot_id: null,
								task_id: null,
								available_tasks: [],
								match_status: "none",
								is_matching: false, // 개별 매칭 진행 상태
							};
						}
						groups[groupKey].all_versions.push(file);
					});

					Object.values(groups).forEach((g: any) => {
						g.all_versions.sort(
							(a, b) => (b.version || 0) - (a.version || 0),
						);
						const latest = g.all_versions[0];
						g.file_path = latest.file_path;
						g.filename = latest.filename;
						g.version = latest.version;
					});

					displayGroups = Object.values(groups);

					// 2. 비동기 매칭 시작
					startAsyncMatching();
				}
			} else {
				const data = await response.json();
				error = data.detail || "Failed to scan";
			}
		} catch (e) {
			error = "Backend connection failed";
		} finally {
			loading = false;
		}
	}

	async function startAsyncMatching() {
		matching = true;
		// 병렬 요청 수를 제한하기 위해 순차적으로 처리하거나 Promise.all을 적절히 사용
		// 여기서는 사용자가 하나씩 추가되는 것을 보고 싶어 하므로 순차적/약간의 병렬 처리
		const matchPromises = displayGroups.map(async (group) => {
			if (!group.shot_name) return; // 파싱 실패한 건 건너뜀

			group.is_matching = true;
			try {
				const response = await fetch("/files/match-single", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						project_id: selectedProjectId,
						episode_name: group.episode_name,
						sequence_name: group.sequence_name,
						shot_name: group.shot_name,
						task_name: group.task_name,
					}),
				});
				if (response.ok) {
					const result = await response.json();
					console.log(
						`DEBUG: Match Result for ${group.shot_name}: File v${group.version}, Kitsu v${result.last_version}`,
					);

					// 객체 복사 및 업데이트를 통해 반응성 보장
					const isPublished =
						result.task_id &&
						result.last_version !== null &&
						group.version <= result.last_version;

					const updatedGroup = {
						...group,
						shot_id: result.shot_id,
						task_id: result.task_id,
						available_tasks: result.available_tasks,
						match_status: result.match_status,
						last_version: result.last_version,
						is_published: isPublished,
						selected: result.task_id && !isPublished, // 미등록 버전일 때만 자동 선택
						is_matching: false,
					};

					// 배열 내 해당 항목 교체
					const idx = displayGroups.findIndex((g) => g === group);
					if (idx !== -1) displayGroups[idx] = updatedGroup;
				}
			} catch (e) {
				console.error("Match error", e);
			} finally {
				group.is_matching = false;
			}
		});

		await Promise.all(matchPromises);
		matching = false;
	}

	function handleVersionChange(group, index) {
		const selected = group.all_versions[index];
		group.file_path = selected.file_path;
		group.filename = selected.filename;
		group.version = selected.version;
		group.selected_file_index = index;
	}

	function handleTaskChange(group, newTaskId) {
		group.task_id = newTaskId;
		group.selected = !!newTaskId;
	}

	function applyGlobalStatus() {
		displayGroups = displayGroups.map((g) => {
			if (g.selected) return { ...g, status_id: globalStatusId };
			return g;
		});
	}

	function applyGlobalTask(taskTypeName) {
		if (!taskTypeName) return;
		displayGroups = displayGroups.map((g) => {
			if (g.selected || g.shot_id) {
				const matched = g.available_tasks.find(
					(t) => t.name === taskTypeName,
				);
				if (matched) {
					return { ...g, task_id: matched.id, selected: true };
				}
			}
			return g;
		});
	}

	async function handlePublish() {
		const itemsToPublish = displayGroups.filter(
			(g) => g.selected && g.task_id,
		);
		if (itemsToPublish.length === 0) return;

		publishing = true;
		error = "";
		publishResults = { success: 0, failed: 0 };

		try {
			for (let i = 0; i < displayGroups.length; i++) {
				const group = displayGroups[i];
				if (!group.selected || !group.task_id) continue;

				// 개별 상태 업데이트
				displayGroups[i] = { ...group, publish_status: "uploading" };
				appendLog(
					`[PUBLISH] Processing ${i + 1}/${itemsToPublish.length}: ${group.filename}`,
				);

				try {
					const payload = {
						items: [
							{
								file_path: group.file_path,
								shot_id: group.shot_id,
								task_id: group.task_id,
								comment: group.comment,
								task_status_id: group.status_id,
							},
						],
					};

					const response = await fetch("/publish/execute", {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify(payload),
					});

					if (response.ok) {
						const results = await response.json();
						if (results[0] && results[0].status === "success") {
							displayGroups[i] = {
								...displayGroups[i],
								publish_status: "success",
								is_published: true,
								selected: false,
							};
							publishResults.success++;
						} else {
							const errorMsg =
								results[0]?.message || "Unknown error";
							displayGroups[i] = {
								...displayGroups[i],
								publish_status: "error",
								error_message: errorMsg,
							};
							publishResults.failed++;
							appendLog(`[ERROR] ${group.filename}: ${errorMsg}`);
						}
					} else {
						displayGroups[i] = {
							...displayGroups[i],
							publish_status: "error",
						};
						publishResults.failed++;
					}
				} catch (err: any) {
					displayGroups[i] = {
						...displayGroups[i],
						publish_status: "error",
					};
					publishResults.failed++;
					appendLog(`[EXCEPTION] ${group.filename}: ${err.message}`);
				}
			}

			if (publishResults.success > 0 || publishResults.failed > 0) {
				showSuccessModal = true;
			}
		} catch (e: any) {
			error = "Error during publish process.";
			appendLog(`[CRITICAL] Publish process interrupted: ${e.message}`);
		} finally {
			publishing = false;
		}
	}

	async function openFolderDialog() {
		// pywebview가 주입한 API가 있는지 확인
		if (
			window.pywebview &&
			window.pywebview.api &&
			window.pywebview.api.select_folder
		) {
			try {
				const path = await window.pywebview.api.select_folder();
				if (path) {
					directoryPath = path;
					// 선택하자마자 스캔 실행 (사용자 편의성)
					scanDirectory();
				}
			} catch (e) {
				console.error("Failed to open folder dialog", e);
			}
		} else {
			alert(
				"Folder picker is only available in Desktop App mode. Please enter the path manually.",
			);
		}
	}
</script>

<div
	class="min-h-screen bg-slate-950 font-sans text-slate-100 pb-20 selection:bg-blue-500 selection:text-white"
>
	{#if checkingSession || loading}
		<div
			class="fixed inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-50 animate-in fade-in duration-300"
		>
			<div
				class="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full shadow-lg shadow-blue-500/20 mb-4"
			></div>
			<p class="text-slate-400 font-medium animate-pulse">
				{checkingSession ? "Checking Session..." : "Listing Files..."}
			</p>
		</div>
	{/if}

	{#if !checkingSession}
		<nav
			class="bg-slate-900/50 backdrop-blur-md border-b border-slate-800 px-6 py-4 sticky top-0 z-20"
		>
			<div class="px-8 flex justify-between items-center">
				<div class="flex items-center gap-3">
					<img
						src={logo}
						alt="Logo"
						class="w-8 h-8 object-contain drop-shadow-md"
					/>
					<h1 class="font-bold text-lg tracking-tight">
						Kitsu Publisher
					</h1>
					{#if updateInfo}
						<button
							onclick={() =>
								fetch("/system/open-url", {
									method: "POST",
									headers: {
										"Content-Type": "application/json",
									},
									body: JSON.stringify({
										url: updateInfo.download_url,
									}),
								})}
							class="ml-4 bg-gradient-to-r from-pink-500 to-violet-600 text-white text-xs font-bold px-3 py-1.5 rounded-full animate-pulse hover:animate-none hover:scale-105 transition-transform flex items-center gap-2 shadow-lg shadow-purple-500/20"
						>
							<span>New Update v{updateInfo.latest_version}</span>
							<svg
								class="w-3 h-3"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="3"
									d="M14 5l7 7m0 0l-7 7m7-7H3"
								/></svg
							>
						</button>
					{/if}
				</div>
				<div class="flex items-center gap-4 text-sm">
					<a
						href="/settings"
						class="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-colors"
						title="Settings"
					>
						<svg
							class="w-5 h-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</a>
					<div class="text-slate-400 text-right hidden sm:block">
						<p class="font-medium text-slate-200">{$user?.email}</p>
						<p class="text-xs opacity-60">
							{$kitsuHost
								?.replace("https://", "")
								.replace("/api", "")}
						</p>
					</div>
					<button
						onclick={async () => {
							if (
								window.pywebview &&
								window.pywebview.api &&
								window.pywebview.api.clear_session
							) {
								await window.pywebview.api.clear_session();
							}
							localStorage.removeItem("kitsu_tokens");
							user.set(null);
							goto("/");
						}}
						class="text-slate-400 hover:text-red-400 font-medium transition-colors px-3 py-1.5 hover:bg-white/5 rounded-md"
						>Logout</button
					>
				</div>
			</div>
		</nav>

		<main class="w-full px-8 py-8 space-y-8">
			<section
				class="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 overflow-hidden"
			>
				<div
					class="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center"
				>
					<h2
						class="font-semibold text-slate-100 flex items-center gap-3"
					>
						<span
							class="w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold"
							>1</span
						>Setup Configuration
					</h2>
				</div>
				<div class="p-6 grid grid-cols-1 md:grid-cols-12 gap-6">
					<div class="md:col-span-4 space-y-2">
						<label
							class="block text-xs font-semibold text-slate-500 uppercase tracking-wider"
							for="project-select">Target Project</label
						>
						<div class="relative">
							<select
								id="project-select"
								bind:value={selectedProjectId}
								class="w-full appearance-none bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-200 py-3 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
							>
								<option value="" disabled selected
									>Select a project...</option
								>
								{#each projects as p}<option value={p.id}
										>{p.name}</option
									>{/each}
							</select>
							<div
								class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-500"
							>
								<svg
									class="h-4 w-4 fill-current"
									viewBox="0 0 20 20"
									><path
										d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
									/></svg
								>
							</div>
						</div>
					</div>
					<div class="md:col-span-8 space-y-2">
						<label
							class="block text-xs font-semibold text-slate-500 uppercase tracking-wider"
							for="source-dir">Source Directory</label
						>
						<div class="flex gap-2">
							<div class="relative flex-1 group">
								<input
									id="source-dir"
									type="text"
									bind:value={directoryPath}
									onkeydown={(e) =>
										e.key === "Enter" && scanDirectory()}
									placeholder="/path/to/your/renders"
									class="w-full bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-200 py-3 pl-4 pr-12 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
								/>
								<button
									onclick={openFolderDialog}
									class="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-500 hover:text-blue-400 transition-colors"
									title="Open Folder Picker"
								>
									<svg
										class="w-5 h-5"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
										/>
									</svg>
								</button>
							</div>
							<button
								onclick={scanDirectory}
								disabled={loading || !selectedProjectId}
								class="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 px-6 rounded-xl transition-all disabled:opacity-50 flex items-center gap-2 active:scale-95 shadow-lg shadow-blue-900/20"
							>
								{#if loading}<svg
										class="animate-spin h-4 w-4"
										viewBox="0 0 24 24"
										><circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
											fill="none"
										></circle><path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
										></path></svg
									>Listing{:else}Scan{/if}
							</button>
						</div>
					</div>
				</div>
				{#if error}<div class="px-6 pb-6 animate-in fade-in">
						<div
							class="bg-red-500/10 text-red-400 text-sm p-4 rounded-xl border border-red-500/20 flex items-center gap-3"
						>
							<svg
								class="w-5 h-5 shrink-0"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
								/></svg
							>{error}
						</div>
					</div>{/if}
			</section>

			{#if displayGroups.length > 0}
				<section
					class="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500"
				>
					<div
						class="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 overflow-hidden"
					>
						<div
							class="p-6 border-b border-slate-800 bg-slate-900/50 flex flex-col sm:flex-row justify-between items-end sm:items-center gap-4"
						>
							<h2
								class="font-semibold text-slate-100 flex items-center gap-3"
							>
								<span
									class="w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-lg shadow-blue-600/30"
									>2</span
								>
								Review & Publish
								{#if matching}
									<span
										class="inline-flex items-center gap-2 text-[10px] text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full animate-pulse border border-blue-400/20 ml-2 uppercase font-bold tracking-widest"
										>Matching with Kitsu...</span
									>
								{:else}
									<span
										class="text-slate-500 font-normal text-sm ml-2"
										>({displayGroups.filter(
											(g) => g.selected,
										).length} units)</span
									>
								{/if}
							</h2>

							<div
								class="flex items-center gap-3 bg-slate-800 p-2 rounded-xl border border-slate-700 shadow-sm"
							>
								<span
									class="text-[10px] font-bold text-slate-500 pl-2 uppercase tracking-widest"
									>Set Selected:</span
								>
								<div class="relative">
									<select
										onchange={(e) =>
											applyGlobalTask(e.target.value)}
										class="text-xs appearance-none border-none bg-slate-700 text-slate-200 rounded-lg py-1.5 pl-2 pr-7 focus:ring-0 cursor-pointer hover:bg-slate-600 transition-colors"
									>
										<option value="">-- Task --</option>
										{#each uniqueTaskTypes as taskName}<option
												value={taskName}
												>{taskName}</option
											>{/each}
									</select>
									<div
										class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500"
									>
										<svg
											class="h-3 w-3 fill-current"
											viewBox="0 0 20 20"
											><path
												d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
											/></svg
										>
									</div>
								</div>
								<div class="relative">
									<select
										bind:value={globalStatusId}
										onchange={applyGlobalStatus}
										class="text-xs appearance-none border-none bg-slate-700 text-slate-200 rounded-lg py-1.5 pl-2 pr-7 focus:ring-0 cursor-pointer hover:bg-slate-600 transition-colors"
									>
										{#each statusTypes as s}<option
												value={s.id}>{s.name}</option
											>{/each}
									</select>
									<div
										class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500"
									>
										<svg
											class="h-3 w-3 fill-current"
											viewBox="0 0 20 20"
											><path
												d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
											/></svg
										>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-x-auto">
							<table class="w-full text-left border-collapse">
								<thead>
									<tr
										class="bg-slate-950/30 border-b border-slate-800 text-[10px] font-bold text-slate-500 uppercase tracking-widest"
									>
										<th class="px-6 py-4 w-12 text-center">
											<input
												type="checkbox"
												onchange={(e) => {
													const checked =
														e.target.checked;
													displayGroups =
														displayGroups.map(
															(g) => ({
																...g,
																selected:
																	checked &&
																	!!g.task_id,
															}),
														);
												}}
												class="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500 cursor-pointer"
											/>
										</th>
										<th
											class="px-6 py-4 cursor-pointer hover:text-slate-300 transition-colors"
											onclick={() =>
												toggleSort("filename")}
										>
											File Info
											{#if sortConfig.key === "filename"}
												<span class="ml-1 text-blue-500"
													>{sortConfig.direction ===
													"asc"
														? "↑"
														: "↓"}</span
												>
											{/if}
										</th>
										<th
											class="px-6 py-4 w-24 text-center cursor-pointer hover:text-slate-300 transition-colors"
											onclick={() =>
												toggleSort("version")}
										>
											Version
											{#if sortConfig.key === "version"}
												<span class="ml-1 text-blue-500"
													>{sortConfig.direction ===
													"asc"
														? "↑"
														: "↓"}</span
												>
											{/if}
										</th>
										<th
											class="px-6 py-4 cursor-pointer hover:text-slate-300 transition-colors"
											onclick={() =>
												toggleSort("priority")}
										>
											Match
											{#if sortConfig.key === "priority"}
												<span class="ml-1 text-blue-500"
													>{sortConfig.direction ===
													"asc"
														? "↑"
														: "↓"}</span
												>
											{/if}
										</th>
										<th class="px-6 py-4 w-44">Task</th>
										<th class="px-6 py-4 w-40">Status</th>
										<th class="px-6 py-4 w-64">Comment</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-slate-800/50">
									{#each sortedGroups as group}
										<tr
											class="group hover:bg-white/5 transition-colors {group.task_id
												? ''
												: 'bg-yellow-900/5'}"
										>
											<td class="px-6 py-4 text-center"
												><input
													type="checkbox"
													bind:checked={
														group.selected
													}
													disabled={!group.task_id}
													class="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500 disabled:opacity-30 cursor-pointer"
												/></td
											>
											<td class="px-6 py-4">
												<div class="flex flex-col">
													<div
														class="flex items-center gap-2"
													>
														{#if group.publish_status === "uploading"}
															<div
																class="animate-spin h-3 w-3 border-2 border-blue-500 border-t-transparent rounded-full"
															></div>
														{:else if group.publish_status === "success"}
															<svg
																class="w-3.5 h-3.5 text-green-500"
																fill="none"
																viewBox="0 0 24 24"
																stroke="currentColor"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="3"
																	d="M5 13l4 4L19 7"
																/>
															</svg>
														{:else if group.publish_status === "error"}
															<svg
																class="w-3.5 h-3.5 text-red-500"
																fill="none"
																viewBox="0 0 24 24"
																stroke="currentColor"
																title={group.error_message}
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="3"
																	d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
																/>
															</svg>
														{/if}
														<span
															class="text-sm font-medium {group.publish_status ===
															'uploading'
																? 'text-blue-400'
																: 'text-slate-200'} truncate max-w-[800px] xl:max-w-[1200px]"
															title={group.filename}
															>{group.filename}</span
														>
													</div>
													<span
														class="text-[9px] text-slate-500 truncate max-w-[800px] xl:max-w-[1200px] font-mono opacity-60 tracking-tighter"
														>{group.file_path}</span
													>
												</div>
											</td>
											<td class="px-6 py-4">
												{#if group.all_versions.length > 1}
													<div class="relative">
														<select
															onchange={(e) =>
																handleVersionChange(
																	group,
																	parseInt(
																		e.target
																			.value,
																	),
																)}
															class="w-full text-center appearance-none text-[11px] bg-slate-800 border border-slate-700 text-blue-400 font-bold rounded-lg py-1 px-2 focus:ring-1 focus:ring-blue-500 transition-all cursor-pointer hover:bg-slate-700"
														>
															{#each group.all_versions as v, i}<option
																	value={i}
																	>v{String(
																		v.version,
																	).padStart(
																		3,
																		"0",
																	)}</option
																>{/each}
														</select>
													</div>
												{:else}
													<div
														class="text-center text-[11px] text-slate-400 font-bold"
													>
														v{String(
															group.version,
														).padStart(3, "0")}
													</div>
												{/if}
											</td>
											<td class="px-6 py-4">
												{#if group.is_matching}
													<div
														class="flex items-center gap-2"
													>
														<div
															class="animate-spin h-3 w-3 border-2 border-blue-500 border-t-transparent rounded-full"
														></div>
														<span
															class="text-[9px] text-slate-500 font-bold uppercase tracking-wider"
															>Matching...</span
														>
													</div>
												{:else if group.shot_id}
													<div
														class="flex items-center gap-2"
													>
														<span
															class="font-bold text-slate-200 text-xs"
															>{group.shot_name}</span
														>
														{#if group.is_published}
															<span
																class="bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider"
																>PUBLISHED</span
															>
														{:else if group.match_status === "full"}
															<span
																class="bg-green-500/10 text-green-400 border border-green-500/20 px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider"
																>OK</span
															>
														{:else}
															<span
																class="bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider"
																>SHOT</span
															>
														{/if}
													</div>
													{#if group.last_version !== null}
														<div
															class="text-[9px] text-slate-500 mt-0.5"
														>
															Latest in Kitsu: v{String(
																group.last_version,
															).padStart(3, "0")}
														</div>
													{/if}
												{:else}
													<div
														class="flex items-center gap-2"
													>
														<div
															class="bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded text-[9px] font-bold"
														>
															MISS
														</div>
														<span
															class="text-[10px] text-slate-600 italic"
															>{group.shot_name ||
																"N/A"}</span
														>
													</div>
												{/if}
											</td>
											<td class="px-6 py-4">
												{#if group.shot_id}
													<div class="relative">
														<select
															value={group.task_id}
															onchange={(e) =>
																handleTaskChange(
																	group,
																	e.target
																		.value,
																)}
															class="w-full appearance-none text-[11px] bg-slate-800 border {group.task_id
																? 'border-slate-700'
																: 'border-red-500/40'} text-slate-200 rounded-lg py-1.5 pl-2 pr-6 focus:ring-1 focus:ring-blue-500 transition-all cursor-pointer"
														>
															<option
																value=""
																disabled
																selected={!group.task_id}
																>Select Task...</option
															>
															{#each group.available_tasks as task}<option
																	value={task.id}
																	>{task.name}</option
																>{/each}
														</select>
														<div
															class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500"
														>
															<svg
																class="h-3 w-3 fill-current"
																viewBox="0 0 20 20"
																><path
																	d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
																/></svg
															>
														</div>
													</div>
												{:else}<span
														class="text-slate-700"
														>—</span
													>{/if}
											</td>
											<td class="px-6 py-4">
												<div class="relative">
													<select
														bind:value={
															group.status_id
														}
														disabled={!group.task_id}
														class="w-full appearance-none text-[11px] bg-slate-800 border border-slate-700 text-slate-200 rounded-lg py-1.5 pl-2 pr-6 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:bg-slate-900 transition-all"
													>
														{#each statusTypes as s}<option
																value={s.id}
																>{s.name}</option
															>{/each}
													</select>
													<div
														class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500"
													>
														<svg
															class="h-3 w-3 fill-current"
															viewBox="0 0 20 20"
															><path
																d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
															/></svg
														>
													</div>
												</div>
											</td>
											<td class="px-6 py-4"
												><input
													type="text"
													bind:value={group.comment}
													disabled={!group.task_id}
													placeholder={group.task_id
														? "Add a comment..."
														: "Select task"}
													class="w-full text-[11px] bg-slate-800 border border-slate-800 text-slate-200 rounded-lg py-1.5 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-slate-600 disabled:opacity-30 transition-all"
												/></td
											>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				</section>

				<div
					class="fixed bottom-0 left-0 right-0 p-4 bg-slate-900/80 backdrop-blur-lg border-t border-slate-800 shadow-2xl flex justify-center items-center gap-6 z-30"
				>
					<div class="text-sm text-slate-400">
						Ready to publish <strong
							class="text-white text-base mx-1"
							>{displayGroups.filter((g) => g.selected)
								.length}</strong
						> shots
					</div>
					<button
						onclick={handlePublish}
						disabled={publishing ||
							displayGroups.filter((g) => g.selected).length ===
								0}
						class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transform active:scale-95"
					>
						{#if publishing}<svg
								class="animate-spin h-5 w-5"
								viewBox="0 0 24 24"
								><circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
									fill="none"
								></circle><path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
								></path></svg
							>Publishing...{:else}🚀 Publish Now{/if}
					</button>
				</div>
			{/if}
		</main>

		{#if showSuccessModal}
			<div
				class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200"
			>
				<div
					class="bg-slate-900 rounded-2xl shadow-2xl border border-slate-800 p-8 max-w-sm w-full text-center space-y-6"
				>
					<div
						class="w-20 h-20 bg-green-500/10 text-green-500 rounded-full flex items-center justify-center mx-auto text-4xl shadow-lg shadow-green-500/20"
					>
						🎉
					</div>
					<div>
						<h3 class="text-2xl font-bold text-white mb-2">
							Publish Complete!
						</h3>
						<p class="text-slate-400">
							Successfully published <strong
								class="text-green-400 text-lg"
								>{publishResults.success}</strong
							> shots.
						</p>
						{#if publishResults.failed > 0}<p
								class="text-red-400 text-sm mt-2"
							>
								Failed: {publishResults.failed}
							</p>{/if}
					</div>
					<button
						onclick={() => (showSuccessModal = false)}
						class="w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 rounded-xl transition-all border border-slate-700"
						>Close</button
					>
				</div>
			</div>
		{/if}
	{/if}

	<!-- Log Viewer Button -->
	<button
		onclick={toggleLogs}
		class="fixed bottom-4 right-4 z-40 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white p-3 rounded-full shadow-lg border border-slate-700 transition-all active:scale-95"
		title="Toggle Logs"
	>
		<svg
			class="w-5 h-5"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
			/>
		</svg>
	</button>

	<!-- About Button (Fixed Position) -->
	<button
		onclick={() => (aboutOpen = true)}
		class="fixed bottom-6 right-20 z-40 text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-2 text-xs font-bold uppercase tracking-widest group"
		title="About"
	>
		<span
			class="opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
			>About</span
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
				d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
			/>
		</svg>
	</button>

	<!-- Log Viewer Panel -->
	{#if showLogs}
		<div
			class="fixed bottom-20 right-4 w-96 h-80 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-2xl shadow-2xl z-40 flex flex-col overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-200"
		>
			<div
				class="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-800/50"
			>
				<span
					class="text-xs font-bold text-slate-400 uppercase tracking-wider"
					>System Logs</span
				>
				<div class="flex gap-2">
					<button
						onclick={() => (logs = [])}
						class="text-[10px] text-slate-500 hover:text-red-400 transition-colors"
						>Clear</button
					>
					<button
						onclick={toggleLogs}
						class="text-slate-500 hover:text-white transition-colors"
						aria-label="Close Logs"
					>
						<svg
							class="w-4 h-4"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							><path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/></svg
						>
					</button>
				</div>
			</div>
			<div
				bind:this={logContainer}
				class="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-[10px] text-slate-300"
			>
				{#if logs.length === 0}
					<div class="text-center text-slate-600 italic py-4">
						No logs yet...
					</div>
				{:else}
					{#each logs as log}
						<div
							class="break-all border-b border-slate-800/50 pb-0.5 mb-0.5 last:border-0"
						>
							<span
								class={log.includes("ERROR")
									? "text-red-400"
									: log.includes("WARNING")
										? "text-yellow-400"
										: "text-slate-400"}
							>
								{log}
							</span>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
	<AboutModal bind:isOpen={aboutOpen} />
</div>
