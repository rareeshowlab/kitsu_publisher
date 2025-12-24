<script lang="ts">
	import { user, kitsuHost } from '$lib/store';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import logo from '$lib/assets/logo.png';

	let host = $state('https://');
	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let error = $state('');

	onMount(() => {
		// 로그인 페이지에 들어왔을 때 이미 로컬스토리지에 토큰이 있고, Store에도 유저가 있으면 publish로 리다이렉트
		// 하지만 Store는 새로고침 시 날아가므로, 여기서 세션 복구 로직을 실행하는 게 안전
		const storedTokens = localStorage.getItem('kitsu_tokens');
		if (storedTokens && !$user) {
			goto('/publish'); // publish 페이지에서 복구 로직 실행하도록 넘김
		} else if ($user) {
			goto('/publish');
		}
	});

	async function handleLogin() {
		loading = true;
		error = '';
		try {
			const response = await fetch('/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ host, email, password })
			});

			if (response.ok) {
				const data = await response.json();
				
				// Store 저장
				user.set(data.user);
				kitsuHost.set(data.host); // 백엔드에서 정제된 호스트 사용
				
				// LocalStorage 저장
				localStorage.setItem('kitsu_tokens', JSON.stringify(data.tokens));
				localStorage.setItem('kitsu_host', data.host);

				goto('/publish');
			} else {
				const data = await response.json();
				error = data.detail || 'Login failed';
			}
		} catch (e) {
			error = 'Could not connect to the backend server.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden text-slate-100 selection:bg-blue-500 selection:text-white">
	<!-- Decorative Background -->
	<div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-slate-950"></div>
	<div class="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
		<div class="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[100px] animate-pulse"></div>
		<div class="absolute -bottom-[20%] -right-[10%] w-[50%] h-[50%] bg-purple-600/10 rounded-full blur-[100px] animate-pulse animation-delay-2000"></div>
	</div>

	<div class="max-w-md w-full bg-slate-900/50 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-slate-800 relative z-10">
		<div class="text-center mb-8">
			<div class="w-20 h-20 mx-auto mb-4 relative group">
				<div class="absolute inset-0 bg-blue-600/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"></div>
				<img src={logo} alt="Kitsu Publisher Logo" class="w-full h-full object-contain relative z-10 drop-shadow-lg" />
			</div>
			<h1 class="text-3xl font-bold text-white tracking-tight">Kitsu Publisher</h1>
			<p class="text-slate-400 text-sm mt-2">Sign in to batch upload your shots</p>
		</div>
		
		<form onsubmit={(e) => { e.preventDefault(); handleLogin(); }} class="space-y-5">
			<div class="space-y-1.5">
				<label class="block text-xs font-bold text-slate-500 uppercase tracking-wider pl-1" for="host">Kitsu Host URL</label>
				<div class="relative">
					<input
						id="host"
						type="text"
						bind:value={host}
						placeholder="https://your-studio.kitsu.io"
						class="w-full pl-4 pr-4 py-3 bg-slate-800/50 border border-slate-700 text-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm placeholder-slate-600"
						required
					/>
				</div>
			</div>

			<div class="space-y-1.5">
				<label class="block text-xs font-bold text-slate-500 uppercase tracking-wider pl-1" for="email">Email Address</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					placeholder="name@studio.com"
					class="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 text-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm placeholder-slate-600"
					required
				/>
			</div>

			<div class="space-y-1.5">
				<label class="block text-xs font-bold text-slate-500 uppercase tracking-wider pl-1" for="password">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					placeholder="••••••••"
					class="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 text-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm placeholder-slate-600"
					required
				/>
			</div>

			{#if error}
				<div class="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2 animate-in fade-in slide-in-from-top-2">
					<svg class="w-5 h-5 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<p class="text-red-400 text-xs font-medium pt-0.5">{error}</p>
				</div>
			{/if}

			<button
				type="submit"
				disabled={loading}
				class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl transition-all duration-200 ease-in-out transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20 hover:shadow-blue-600/30 flex justify-center items-center gap-2 mt-2"
			>
				{#if loading}
					<svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span>Connecting...</span>
				{:else}
					<span>Sign In</span>
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
					</svg>
				{/if}
			</button>
		</form>
	</div>
</div>

<style>
	.animation-delay-2000 {
		animation-delay: 2s;
	}
</style>
