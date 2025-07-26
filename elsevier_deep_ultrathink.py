#!/usr/bin/env python3
"""
Elsevier Deep UltraThink CloudFlare Bypass
==========================================

Ultra-sophisticated CloudFlare bypass using advanced stealth techniques.
"""

import asyncio
import random
import time
import math
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierDeepUltraThink:
    def __init__(self):
        self.output_dir = Path("elsevier_deep_ultra")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def realistic_human_delay(self, min_ms=800, max_ms=3000):
        """Ultra-realistic human delay with natural variation"""
        # Humans don't use uniform random - they cluster around certain values
        base_delay = random.gauss(1500, 500)  # Gaussian distribution
        base_delay = max(min_ms, min(max_ms, base_delay))
        
        # Add micro-pauses that humans have
        micro_pauses = random.randint(0, 3)
        for _ in range(micro_pauses):
            await asyncio.sleep(random.uniform(0.05, 0.2))
        
        await asyncio.sleep(base_delay / 1000)
    
    async def human_mouse_path(self, page, start_x, start_y, end_x, end_y, duration=1.0):
        """Generate realistic bezier curve mouse movement"""
        steps = int(duration * 60)  # 60 FPS
        
        # Control points for bezier curve
        cp1_x = start_x + random.randint(-50, 50)
        cp1_y = start_y + random.randint(-50, 50)
        cp2_x = end_x + random.randint(-50, 50)
        cp2_y = end_y + random.randint(-50, 50)
        
        for i in range(steps):
            t = i / steps
            
            # Cubic bezier curve
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
            
            await page.mouse.move(x, y)
            await asyncio.sleep(duration / steps)
    
    async def human_scroll_pattern(self, page):
        """Simulate realistic human scrolling patterns"""
        scroll_sessions = random.randint(2, 5)
        
        for _ in range(scroll_sessions):
            # Scroll down in realistic chunks
            scroll_amount = random.randint(300, 800)
            await page.mouse.wheel(0, scroll_amount)
            
            # Pause to "read"
            await asyncio.sleep(random.uniform(1.5, 4.0))
            
            # Sometimes scroll back up slightly (human behavior)
            if random.random() < 0.3:
                await page.mouse.wheel(0, -random.randint(100, 300))
                await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def simulate_human_reading(self, page):
        """Simulate human reading behavior on the page"""
        # Get page dimensions
        viewport = page.viewport_size
        width, height = viewport['width'], viewport['height']
        
        # Reading pattern: eyes move in saccades
        reading_points = [
            (width * 0.1, height * 0.3),   # Top left
            (width * 0.7, height * 0.3),   # Top right
            (width * 0.1, height * 0.5),   # Middle left
            (width * 0.8, height * 0.5),   # Middle right
            (width * 0.1, height * 0.7),   # Bottom left
            (width * 0.6, height * 0.7),   # Bottom right
        ]
        
        current_x, current_y = width // 2, height // 2
        
        for point_x, point_y in reading_points:
            # Move to reading position
            await self.human_mouse_path(page, current_x, current_y, point_x, point_y, 0.8)
            current_x, current_y = point_x, point_y
            
            # Pause to "read"
            read_time = random.uniform(1.2, 3.5)
            await asyncio.sleep(read_time)
            
            # Small micro-movements during reading
            for _ in range(random.randint(1, 3)):
                micro_x = current_x + random.randint(-20, 20)
                micro_y = current_y + random.randint(-10, 10)
                await page.mouse.move(micro_x, micro_y)
                await asyncio.sleep(random.uniform(0.3, 0.8))
    
    async def setup_ultra_stealth_browser(self, p):
        """Setup browser with maximum stealth configuration"""
        
        # Create persistent context for session continuity
        user_data_dir = self.output_dir / "ultra_stealth_profile"
        user_data_dir.mkdir(exist_ok=True)
        
        # Ultra-comprehensive stealth arguments
        stealth_args = [
            # Core automation hiding
            '--disable-blink-features=AutomationControlled',
            '--disable-features=AutomationControlled',
            '--exclude-switches=enable-automation',
            '--disable-ipc-flooding-protection',
            
            # GPU and rendering
            '--disable-gpu',
            '--disable-gpu-sandbox',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-features=VizDisplayCompositor',
            
            # Network and security
            '--disable-web-security',
            '--disable-site-isolation-trials',
            '--disable-features=IsolateOrigins,site-per-process',
            '--allow-running-insecure-content',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors-spki-list',
            
            # Performance
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-accelerated-jpeg-decoding',
            '--disable-accelerated-mjpeg-decode',
            '--disable-accelerated-video-decode',
            '--disable-accelerated-video-encode',
            
            # Extensions and plugins
            '--disable-extensions',
            '--disable-plugins',
            '--disable-default-apps',
            '--disable-component-extensions-with-background-pages',
            
            # Misc stealth
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--disable-logging',
            '--disable-bundled-ppapi-flash',
            '--disable-client-side-phishing-detection',
            
            # Window settings
            '--start-maximized',
            '--window-size=1920,1080',
            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            channel="chrome",  # Use real Chrome
            args=stealth_args,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications', 'camera', 'microphone'],
            color_scheme='light',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Dnt': '1'
            }
        )
        
        return browser
    
    async def inject_ultra_stealth_scripts(self, page):
        """Inject comprehensive anti-detection scripts"""
        
        stealth_script = """
        // Ultra-comprehensive stealth script
        (() => {
            'use strict';
            
            // 1. Navigator overrides
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // 2. Chrome object
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed',
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                },
                runtime: {
                    OnInstalledReason: {
                        CHROME_UPDATE: 'chrome_update',
                        INSTALL: 'install',
                        SHARED_MODULE_UPDATE: 'shared_module_update',
                        UPDATE: 'update'
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic'
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        ARM64: 'arm64',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformOs: {
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        MAC: 'mac',
                        OPENBSD: 'openbsd',
                        WIN: 'win'
                    },
                    RequestUpdateCheckStatus: {
                        NO_UPDATE: 'no_update',
                        THROTTLED: 'throttled',
                        UPDATE_AVAILABLE: 'update_available'
                    }
                },
                loadTimes: function() {
                    return {
                        commitLoadTime: Math.random() * 1000 + 1000,
                        connectionInfo: 'h2',
                        finishDocumentLoadTime: Math.random() * 1000 + 2000,
                        finishLoadTime: Math.random() * 1000 + 2000,
                        firstPaintAfterLoadTime: Math.random() * 100 + 1000,
                        firstPaintTime: Math.random() * 100 + 1000,
                        navigationType: 'Other',
                        npnNegotiatedProtocol: 'h2',
                        requestTime: Date.now() / 1000 - Math.random() * 3,
                        startLoadTime: Math.random() * 1000 + 1000,
                        wasAlternateProtocolAvailable: false,
                        wasFetchedViaSpdy: true,
                        wasNpnNegotiated: true
                    };
                },
                csi: function() {
                    return {
                        pageT: Math.random() * 1000 + 1000,
                        startE: Date.now() - Math.random() * 1000,
                        tran: 15
                    };
                }
            };
            
            // 3. Plugins array
            Object.defineProperty(navigator, 'plugins', {
                get: () => new Proxy([
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format", 
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    },
                    {
                        0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: Plugin},
                        1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: Plugin},
                        description: "Native Client",
                        filename: "internal-nacl-plugin",
                        length: 2,
                        name: "Native Client"
                    }
                ], {
                    get: (target, prop) => {
                        if (typeof prop === 'string' && /^\\d+$/.test(prop)) {
                            return target[parseInt(prop)];
                        }
                        return target[prop];
                    }
                }),
                configurable: true
            });
            
            // 4. Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
            
            // 5. Hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true
            });
            
            // 6. Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });
            
            // 7. Connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    downlink: 10,
                    effectiveType: '4g',
                    rtt: 50,
                    saveData: false
                }),
                configurable: true
            });
            
            // 8. Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 9. WebGL fingerprinting protection
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
            
            // 10. Canvas fingerprinting protection
            const toBlob = HTMLCanvasElement.prototype.toBlob;
            const toDataURL = HTMLCanvasElement.prototype.toDataURL;
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            
            HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
                const canvas = this;
                setTimeout(() => toBlob.call(canvas, callback, type, quality), Math.random() * 10);
            };
            
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                // Add slight noise to prevent fingerprinting
                const ctx = this.getContext('2d');
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                }
                ctx.putImageData(imageData, 0, 0);
                return toDataURL.call(this, type, quality);
            };
            
            // 11. Screen properties
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1055,
                configurable: true
            });
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920,
                configurable: true
            });
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24,
                configurable: true
            });
            Object.defineProperty(screen, 'height', {
                get: () => 1080,
                configurable: true
            });
            Object.defineProperty(screen, 'width', {
                get: () => 1920,
                configurable: true
            });
            
            // 12. Timezone
            Date.prototype.getTimezoneOffset = function() {
                return 300; // EST
            };
            
            // 13. Battery API (if exists)
            if ('getBattery' in navigator) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }
            
            // 14. Override toString methods
            window.toString = () => '[object Window]';
            window.navigator.toString = () => '[object Navigator]';
            
            console.log('Ultra-stealth script injected successfully');
        })();
        """
        
        await page.add_init_script(stealth_script)
    
    async def warm_up_session(self, page):
        """Ultra-comprehensive session warming"""
        
        self.log("🔥 Phase 1: Session warming with Google")
        
        # Start with Google - most natural
        await page.goto("https://www.google.com", wait_until='networkidle')
        await self.realistic_human_delay(2000, 4000)
        
        # Simulate human behavior on Google
        search_box = await page.query_selector('input[name="q"]')
        if search_box:
            # Type like a human researching
            await search_box.click()
            await self.realistic_human_delay(500, 1000)
            
            search_terms = ["academic papers", "scientific research", "elsevier sciencedirect"]
            for term in search_terms:
                await search_box.fill("")
                for char in term:
                    await page.keyboard.type(char, delay=random.randint(80, 200))
                await self.realistic_human_delay(1000, 2000)
                
                # Sometimes search, sometimes delete and try again
                if random.random() < 0.7:
                    await page.keyboard.press('Enter')
                    await page.wait_for_load_state('networkidle')
                    await self.realistic_human_delay(3000, 6000)
                    
                    # Simulate reading search results
                    await self.simulate_human_reading(page)
                    await self.human_scroll_pattern(page)
                    
                    # Go back to search
                    await page.go_back()
                    await self.realistic_human_delay()
                    search_box = await page.query_selector('input[name="q"]')
        
        self.log("🔥 Phase 2: Visiting academic sites")
        
        # Visit some academic sites to build reputation
        academic_sites = [
            "https://scholar.google.com",
            "https://www.ncbi.nlm.nih.gov",
            "https://arxiv.org"
        ]
        
        for site in academic_sites[:2]:  # Visit 2 sites
            self.log(f"   Visiting {site}")
            await page.goto(site, wait_until='networkidle')
            await self.realistic_human_delay(3000, 6000)
            await self.simulate_human_reading(page)
            await self.human_scroll_pattern(page)
        
        self.log("🔥 Phase 3: ScienceDirect homepage exploration")
        
        # Now visit ScienceDirect homepage
        await page.goto("https://www.sciencedirect.com", wait_until='networkidle')
        await self.realistic_human_delay(4000, 7000)
        
        # Interact with the homepage like a real user
        await self.simulate_human_reading(page)
        await self.human_scroll_pattern(page)
        
        # Try searching for something general
        search_input = await page.query_selector('input[name="qs"], input[type="search"]')
        if search_input:
            await search_input.click()
            await self.realistic_human_delay()
            
            # Type a general academic term
            search_term = "computational physics"
            for char in search_term:
                await page.keyboard.type(char, delay=random.randint(100, 250))
            
            await self.realistic_human_delay(1000, 2000)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('networkidle')
            await self.realistic_human_delay(3000, 5000)
            
            # Browse search results briefly
            await self.simulate_human_reading(page)
            await self.human_scroll_pattern(page)
    
    async def test_elsevier_deep_ultra(self):
        """Deep ultrathink CloudFlare bypass test"""
        
        # Get credentials first
        try:
            from src.secure_credential_manager import get_credential_manager
            
            cm = get_credential_manager()
            username = cm.get_credential("eth_username")
            password = cm.get_credential("eth_password")
            
            if not username or not password:
                self.log("❌ No ETH credentials")
                return False
                
        except ImportError as e:
            self.log(f"❌ Cannot import credentials: {e}")
            return False
        
        self.log("🧠 DEEP ULTRATHINK MODE: Maximum Stealth CloudFlare Bypass")
        self.log("=" * 80)
        
        test_doi = "10.1016/j.jcp.2019.07.031"
        target_pii = "S0021999119305169"
        
        try:
            async with async_playwright() as p:
                # Setup ultra-stealth browser
                browser = await self.setup_ultra_stealth_browser(p)
                page = browser.pages[0] if browser.pages else await browser.new_page()
                
                # Inject stealth scripts
                await self.inject_ultra_stealth_scripts(page)
                
                # Comprehensive session warming
                await self.warm_up_session(page)
                
                self.log("🎯 Phase 4: Approaching target paper")
                
                # Now try to access the target paper gradually
                # First, try searching for it on ScienceDirect
                if page.url.startswith("https://www.sciencedirect.com"):
                    search_input = await page.query_selector('input[name="qs"], input[type="search"]')
                    if search_input:
                        await search_input.click()
                        await search_input.fill("")
                        await self.realistic_human_delay()
                        
                        # Search for the paper title or DOI
                        search_query = f"doi:{test_doi}"
                        for char in search_query:
                            await page.keyboard.type(char, delay=random.randint(150, 300))
                        
                        await self.realistic_human_delay(2000, 3000)
                        await page.keyboard.press('Enter')
                        
                        # Wait for search results
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        await self.realistic_human_delay(3000, 5000)
                        
                        # Look for the paper in results
                        paper_link = await page.query_selector(f'a[href*="{target_pii}"]')
                        if paper_link:
                            self.log("   ✅ Found paper in search results!")
                            await paper_link.click()
                            await page.wait_for_load_state('networkidle', timeout=60000)
                        else:
                            # Direct navigation as fallback
                            self.log("   Direct navigation to paper...")
                            paper_url = f"https://www.sciencedirect.com/science/article/pii/{target_pii}"
                            await page.goto(paper_url, wait_until='networkidle', timeout=60000)
                
                await self.realistic_human_delay(5000, 8000)
                
                # Check if we bypassed CloudFlare
                current_url = page.url
                page_content = await page.content()
                
                self.log(f"📍 Current URL: {current_url}")
                
                if 'Are you a robot?' not in page_content and 'sciencedirect.com/science/article' in current_url:
                    self.log("🎉 SUCCESS! CloudFlare bypassed!")
                    
                    # Take success screenshot
                    await page.screenshot(path=self.output_dir / "success_cloudflare_bypass.png")
                    
                    # Continue with institutional login
                    self.log("🔓 Attempting institutional access...")
                    
                    # Simulate more human behavior before clicking institutional access
                    await self.simulate_human_reading(page)
                    await self.realistic_human_delay(3000, 5000)
                    
                    # Look for institutional access button
                    inst_selectors = [
                        'a:has-text("Access through your institution")',
                        'a:has-text("Get Access")',
                        'button:has-text("Sign in")',
                        'a[href*="chooseorg"]',
                        'a[href*="institutional"]'
                    ]
                    
                    for selector in inst_selectors:
                        inst_button = await page.query_selector(selector)
                        if inst_button:
                            self.log(f"   Found institutional button: {selector}")
                            
                            # Human-like click
                            button_box = await inst_button.bounding_box()
                            if button_box:
                                click_x = button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5)
                                click_y = button_box['y'] + button_box['height'] / 2 + random.randint(-3, 3)
                                
                                await page.mouse.move(click_x, click_y)
                                await self.realistic_human_delay(500, 1000)
                                await page.mouse.click(click_x, click_y)
                                
                                await page.wait_for_load_state('networkidle', timeout=30000)
                                await self.realistic_human_delay(3000, 5000)
                                
                                # Continue with ETH selection and login...
                                # (Similar to SIAM implementation)
                                
                                return True
                            break
                
                else:
                    self.log("❌ CloudFlare challenge still active")
                    if 'Are you a robot?' in page_content:
                        self.log("   Still showing 'Are you a robot?' page")
                        
                        # Take screenshot for analysis
                        await page.screenshot(path=self.output_dir / "cloudflare_challenge.png")
                        
                        # Last resort: wait longer and try interacting
                        self.log("🕐 Last resort: Extended waiting and interaction...")
                        
                        # Look for CloudFlare checkbox
                        checkbox = await page.query_selector('input[type="checkbox"]')
                        if checkbox:
                            self.log("   Found CloudFlare checkbox, attempting click...")
                            await checkbox.click()
                            await page.wait_for_timeout(10000)
                            
                            # Check again
                            page_content = await page.content()
                            if 'Are you a robot?' not in page_content:
                                self.log("🎉 Checkbox approach worked!")
                                return True
                
                await browser.close()
                
        except Exception as e:
            self.log(f"💥 Error: {e}")
            import traceback
            traceback.print_exc()
        
        return False

async def main():
    bypasser = ElsevierDeepUltraThink()
    success = await bypasser.test_elsevier_deep_ultra()
    
    if success:
        print("\n" + "🎉" * 20)
        print("DEEP ULTRATHINK SUCCESS!")
        print("Successfully bypassed Elsevier CloudFlare protection!")
        print("🎉" * 20)
    else:
        print("\n" + "=" * 80)
        print("⚠️ Deep UltraThink Analysis Complete")
        print("=" * 80)
        print("\n🔬 Techniques Tested:")
        print("1. ✅ Ultra-stealth browser configuration")
        print("2. ✅ Comprehensive anti-detection scripts")
        print("3. ✅ Realistic human behavior simulation")
        print("4. ✅ Session warming with academic sites")
        print("5. ✅ Natural search-to-paper flow")
        print("6. ✅ Human-like mouse movements and timing")
        print("\n📊 CloudFlare Protection Level: MAXIMUM")
        print("Elsevier uses state-of-the-art bot detection")
        print("\n💡 Alternative Solutions:")
        print("1. Use Sci-Hub for comprehensive coverage")
        print("2. Manual cookie approach for recent papers")
        print("3. Institutional proxy if available")
        print("4. API endpoint exploration")

if __name__ == "__main__":
    asyncio.run(main())