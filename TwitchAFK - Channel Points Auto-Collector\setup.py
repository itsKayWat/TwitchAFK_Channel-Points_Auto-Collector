import os
import json
import zipfile
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import threading

class TwitchPointsManager:
    def __init__(self):
        self.drivers = {}
        self.running = True
        self.auth_driver = None
        self.authenticated = False
        
    def authenticate(self):
        """Open a visible Chrome window for Twitch login"""
        options = uc.ChromeOptions()
        
        # Essential options to bypass detection
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-gpu')
        
        # Set window size and position
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--window-position=0,0')
        
        # Add recommended user agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        # Additional preferences to make browser look more human
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver with specific configurations
        self.auth_driver = uc.Chrome(
            options=options,
            driver_executable_path=None,
            version_main=122,  # Specify latest Chrome version
            suppress_welcome=True,
            use_subprocess=True
        )
        
        # Set CDP commands to prevent detection
        self.auth_driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        # Navigate to Twitch login
        self.auth_driver.get('https://twitch.tv/login')
        
        print("Please log in to Twitch in the opened browser window.")
        print("After logging in, press Enter to continue...")
        input()
        
        try:
            # Check for login success by looking for user menu
            WebDriverWait(self.auth_driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-a-target="user-menu-toggle"]'))
            )
            
            # Get and store cookies for other instances
            self.cookies = self.auth_driver.get_cookies()
            
            self.authenticated = True
            print("Successfully authenticated!")
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
        
    def create_driver(self, channel):
        options = uc.ChromeOptions()
        options.add_argument('--mute-audio')
        options.add_argument('--headless')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        driver = uc.Chrome(
            options=options,
            suppress_welcome=True,
            use_subprocess=True
        )
        
        # Add authenticated cookies
        if self.cookies:
            driver.get('https://twitch.tv')
            for cookie in self.cookies:
                driver.add_cookie(cookie)
        
        self.drivers[channel] = driver
        
    def manage_channel(self, channel):
        driver = self.drivers[channel]
        driver.get(f'https://twitch.tv/{channel}')
        
        # Wait for stream to load
        wait = WebDriverWait(driver, 20)
        
        try:
            # Set volume to 5%
            volume_script = """
                const video = document.querySelector('video');
                if (video) {
                    video.volume = 0.05;
                    video.muted = false;
                }
            """
            driver.execute_script(volume_script)
            
            while self.running:
                try:
                    # Check for point claim button
                    claim_button = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[aria-label="Claim Bonus"]')
                    ))
                    claim_button.click()
                    
                    # Get current points
                    points_element = driver.find_element(By.CSS_SELECTOR, 
                        '[data-test-selector="balance-string"]')
                    points = int(''.join(filter(str.isdigit, points_element.text)))
                    
                    # Update extension storage
                    update_script = f"""
                        chrome.storage.local.get(['channels'], result => {{
                            const channels = result.channels || {{}};
                            channels['{channel}'] = {{ points: {points} }};
                            chrome.storage.local.set({{ channels: channels }});
                        }});
                    """
                    driver.execute_script(update_script)
                    
                except:
                    time.sleep(30)  # Wait before next check
                    
        except Exception as e:
            print(f"Error in {channel} thread: {e}")
            
    def start(self, channels):
        for channel in channels:
            self.create_driver(channel)
            thread = threading.Thread(target=self.manage_channel, args=(channel,))
            thread.daemon = True
            thread.start()
            
    def stop(self):
        self.running = False
        for driver in self.drivers.values():
            driver.quit()

def create_directory_structure():
    # Create main extension directory
    os.makedirs("twitch_points_manager", exist_ok=True)

def create_manifest():
    manifest = {
        "manifest_version": 3,
        "name": "Twitch Points Manager",
        "version": "1.0",
        "description": "Manage and distribute Twitch channel points",
        "permissions": [
            "storage",
            "tabs",
            "scripting"
        ],
        "host_permissions": [
            "https://*.twitch.tv/*"
        ],
        "action": {
            "default_popup": "popup.html",
            "default_icon": {
                "16": "images/icon16.png",
                "48": "images/icon48.png",
                "128": "images/icon128.png"
            }
        },
        "content_scripts": [{
            "matches": ["https://*.twitch.tv/*"],
            "js": ["content.js"]
        }],
        "background": {
            "service_worker": "background.js"
        }
    }
    
    with open("twitch_points_manager/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

def create_popup_html():
    popup_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Twitch Points Manager</title>
    <style>
        :root {
            --bg-color: #18181b;
            --text-color: #efeff1;
            --border-color: #303032;
            --button-bg: #9147ff;
            --button-hover: #772ce8;
        }
        
        body { 
            width: 350px; 
            padding: 10px;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
        }
        .container { 
            display: flex; 
            flex-direction: column; 
            gap: 10px; 
        }
        button { 
            padding: 8px; 
            cursor: pointer;
            background-color: var(--button-bg);
            color: var(--text-color);
            border: none;
            border-radius: 4px;
        }
        button:hover {
            background-color: var(--button-hover);
        }
        input, select { 
            padding: 5px; 
            margin: 5px 0; 
            width: 100%;
            background-color: #303032;
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }
        .channel-list { 
            margin: 10px 0; 
        }
        .channel-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
        }
        .channel-item:hover {
            background-color: #242425;
        }
        .login-section { 
            text-align: center; 
            margin-bottom: 15px; 
        }
        .add-channel-section { 
            margin-top: 10px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-section" id="loginSection">
            <h3>Python App Status</h3>
            <div id="authStatus">Checking connection...</div>
        </div>

        <div id="mainContent" style="display: none;">
            <div class="add-channel-section">
                <input type="text" id="channelUrl" placeholder="Enter Twitch channel URL or username">
                <button id="addChannel">Add Channel</button>
            </div>

            <div class="channel-list" id="channelList">
                <h3>Accumulated Points:</h3>
                <!-- Channel points will be listed here -->
            </div>

            <div class="send-points-section">
                <h3>Send Points</h3>
                <select id="channelSelect">
                    <!-- Channels will be populated here -->
                </select>
                <input type="text" id="username" placeholder="Recipient Username">
                <input type="number" id="points" placeholder="Points amount">
                <button id="sendPoints">Send Points</button>
            </div>
        </div>
    </div>
    <script src="popup.js"></script>
</body>
</html>
    """
    
    with open("twitch_points_manager/popup.html", "w") as f:
        f.write(popup_html)

def create_popup_js():
    popup_js = """
let twitchAuth = null;
let channels = {};

document.addEventListener('DOMContentLoaded', function() {
    // Check if already logged in
    chrome.storage.local.get(['twitchAuth', 'channels'], function(result) {
        if (result.twitchAuth) {
            twitchAuth = result.twitchAuth;
            channels = result.channels || {};
            showMainContent();
            updateChannelList();
        }
    });

    // Login button listener
    document.getElementById('loginButton').addEventListener('click', async () => {
        const username = document.getElementById('twitchUsername').value;
        const password = document.getElementById('twitchPassword').value;
        
        // Send login request to background script
        chrome.runtime.sendMessage({
            action: 'login',
            username: username,
            password: password
        }, response => {
            if (response.success) {
                twitchAuth = response.auth;
                chrome.storage.local.set({ twitchAuth: twitchAuth });
                showMainContent();
            }
        });
    });

    // Add channel button listener
    document.getElementById('addChannel').addEventListener('click', () => {
        const channelInput = document.getElementById('channelUrl');
        const channelName = extractChannelName(channelInput.value);
        
        if (channelName) {
            chrome.runtime.sendMessage({
                action: 'addChannel',
                channel: channelName
            });
            
            channels[channelName] = { points: 0 };
            chrome.storage.local.set({ channels: channels });
            updateChannelList();
            channelInput.value = '';
        }
    });

    // Send points button listener
    document.getElementById('sendPoints').addEventListener('click', () => {
        const channel = document.getElementById('channelSelect').value;
        const username = document.getElementById('username').value;
        const points = parseInt(document.getElementById('points').value);
        
        if (channel && username && points) {
            chrome.runtime.sendMessage({
                action: 'sendPoints',
                channel: channel,
                recipient: username,
                points: points
            });
        }
    });
});

function showMainContent() {
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
}

function updateChannelList() {
    const channelList = document.getElementById('channelList');
    const channelSelect = document.getElementById('channelSelect');
    
    // Clear existing content
    channelList.innerHTML = '<h3>Accumulated Points:</h3>';
    channelSelect.innerHTML = '';
    
    // Add channels to both list and select
    Object.entries(channels).forEach(([channel, data]) => {
        // Add to points list
        const channelDiv = document.createElement('div');
        channelDiv.className = 'channel-item';
        channelDiv.innerHTML = `
            <span>${channel}</span>
            <span>${formatPoints(data.points)} Channel Points</span>
        `;
        
        // Add double-click handler
        channelDiv.addEventListener('dblclick', () => {
            chrome.tabs.create({ url: `https://twitch.tv/${channel}` });
        });
        
        channelList.appendChild(channelDiv);
        
        // Add to select dropdown
        const option = document.createElement('option');
        option.value = channel;
        option.textContent = channel;
        channelSelect.appendChild(option);
    });
}

function extractChannelName(input) {
    // Handle both URLs and usernames
    if (input.includes('twitch.tv/')) {
        return input.split('twitch.tv/')[1].split('/')[0].toLowerCase();
    }
    return input.toLowerCase();
}

function formatPoints(points) {
    if (points >= 1000) {
        return (points/1000).toFixed(1) + 'K';
    }
    return points;
}
    """
    
    with open("twitch_points_manager/popup.js", "w") as f:
        f.write(popup_js)

def create_content_js():
    content_js = """
// Handle point collection
function collectChannelPoints() {
    const button = document.querySelector('[aria-label="Claim Bonus"]');
    if (button) {
        button.click();
        updatePointsPool();
    }
}

// Update points pool
function updatePointsPool() {
    // Try multiple selectors for point detection
    const pointsElement = document.querySelector('[data-test-selector="balance-string"], [data-test-selector="copo-balance-string"], .channel-points-icon + div');
    
    if (pointsElement) {
        // Remove all non-numeric characters and parse
        const points = parseInt(pointsElement.textContent.replace(/[^0-9]/g, ''));
        if (!isNaN(points)) {
            chrome.storage.local.get(['channels'], result => {
                const channels = result.channels || {};
                const channelName = window.location.pathname.split('/')[1];
                channels[channelName] = { points: points };
                chrome.storage.local.set({ channels: channels });
            });
        }
    }
}

// Update points more frequently
setInterval(updatePointsPool, 2000);

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'collectPoints') {
        collectChannelPoints();
    }
    else if (request.action === 'sendPoints') {
        // This would need to integrate with Twitch's point giving system
        console.log(`Sending ${request.points} points to ${request.username}`);
    }
});
    """
    
    with open("twitch_points_manager/content.js", "w") as f:
        f.write(content_js)

def create_background_js():
    background_js = """
let headlessTabs = {};

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch(request.action) {
        case 'login':
            handleTwitchLogin(request, sendResponse);
            return true;
        
        case 'addChannel':
            createHeadlessTab(request.channel);
            break;
            
        case 'sendPoints':
            sendChannelPoints(request);
            break;
    }
});

async function handleTwitchLogin(request, sendResponse) {
    // In a real implementation, this would securely authenticate with Twitch
    // For demo purposes, we're just simulating successful auth
    sendResponse({
        success: true,
        auth: { username: request.username }
    });
}

async function createHeadlessTab(channel) {
    // Create a hidden tab for the channel
    const tab = await chrome.tabs.create({
        url: `https://twitch.tv/${channel}`,
        active: false
    });

    // Store reference to headless tab
    headlessTabs[channel] = tab.id;

    // Initialize tab with required settings
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: setupHeadlessTab
    });
}

function setupHeadlessTab() {
    // Initial setup with retry mechanism
    const setupInterval = setInterval(() => {
        const videoElement = document.querySelector('video');
        const muteButton = document.querySelector('[aria-label="Mute (m)"]');
        
        if (videoElement && muteButton) {
            // Unmute the stream if muted
            if (muteButton.getAttribute('aria-label') === 'Unmute (m)') {
                muteButton.click();
            }
            
            // Set volume to 5%
            videoElement.volume = 0.05;
            videoElement.muted = false;
            videoElement.play();
            
            clearInterval(setupInterval);
            
            // Start point collection
            startPointCollection();
        }
    }, 2000);
}

function startPointCollection() {
    setInterval(() => {
        // Check and maintain volume/mute settings
        const videoElement = document.querySelector('video');
        const muteButton = document.querySelector('[aria-label="Mute (m)"]');
        
        if (videoElement && muteButton) {
            if (videoElement.muted || videoElement.volume !== 0.05) {
                videoElement.muted = false;
                videoElement.volume = 0.05;
            }
            
            if (muteButton.getAttribute('aria-label') === 'Unmute (m)') {
                muteButton.click();
            }
        }

        // Collect points
        const button = document.querySelector('[aria-label="Claim Bonus"]');
        if (button) {
            button.click();
            updatePoints();
        }
    }, 5000);
}

function updatePoints() {
    const pointsElement = document.querySelector('[data-test-selector="copo-balance-string"]');
    if (pointsElement) {
        const points = parseInt(pointsElement.textContent.replace(/[^0-9]/g, ''));
        chrome.storage.local.get(['channels'], result => {
            const channels = result.channels || {};
            const channelName = window.location.pathname.split('/')[1];
            channels[channelName] = { points: points };
            chrome.storage.local.set({ channels: channels });
        });
    }
}

function sendChannelPoints(request) {
    chrome.tabs.sendMessage(headlessTabs[request.channel], {
        action: 'sendPoints',
        recipient: request.recipient,
        points: request.points
    });
}

// Cleanup on extension update/reload
chrome.runtime.onStartup.addListener(() => {
    Object.values(headlessTabs).forEach(tabId => {
        chrome.tabs.remove(tabId);
    });
    headlessTabs = {};
});
    """
    
    with open("twitch_points_manager/background.js", "w") as f:
        f.write(background_js)

def create_placeholder_icons():
    # Create images directory
    os.makedirs("twitch_points_manager/images", exist_ok=True)
    
    # Basic purple square icon as bytes (minimal viable icon)
    icon_data = {
        16: bytes.fromhex('89504e470d0a1a0a0000000d494844520000001000000010080200000090916836000000017352474200aece1ce90000002149444154388dc592810100300c03bbff9f06144c42091ca2e3ae42492492f8cd2c69df0302d0051f66a74e3c0000000049454e44ae426082'),
        48: bytes.fromhex('89504e470d0a1a0a0000000d494844520000003000000030080200000037ecddaa000000017352474200aece1ce90000002149444154588dc592810100300c03bbff9f06144c42091ca2e3ae42492492f8cd2c69df0302d0051f66a74e3c0000000049454e44ae426082'),
        128: bytes.fromhex('89504e470d0a1a0a0000000d494844520000008000000080080200000040e8d550000000017352474200aece1ce90000002149444154788dc592810100300c03bbff9f06144c42091ca2e3ae42492492f8cd2c69df0302d0051f66a74e3c0000000049454e44ae426082')
    }
    
    # Create icon files
    for size, data in icon_data.items():
        with open(f"twitch_points_manager/images/icon{size}.png", "wb") as f:
            f.write(data)

def create_extension_zip():
    with zipfile.ZipFile("twitch_points_manager.zip", "w") as zf:
        for root, dirs, files in os.walk("twitch_points_manager"):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, "twitch_points_manager")
                zf.write(file_path, arc_name)

def main():
    print("Creating Twitch Points Manager Extension...")
    
    # Create extension files
    create_directory_structure()
    create_manifest()
    create_popup_html()
    create_popup_js()
    create_content_js()
    create_background_js()
    create_placeholder_icons()
    create_extension_zip()
    
    print("\nExtension created successfully!")
    
    # Initialize the point manager
    manager = TwitchPointsManager()
    
    # Authenticate first
    if not manager.authenticate():
        print("Failed to authenticate. Please try again.")
        return
    
    # Get cookies from authenticated session
    cookies = manager.auth_driver.get_cookies()
    
    try:
        # Start monitoring channels
        channels = ['myth']  # You can load this from storage/config
        manager.start(channels, cookies)
        
        print(f"\nMonitoring channels: {', '.join(channels)}")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping point manager...")
        manager.stop()
        print("Point manager stopped")

if __name__ == "__main__":
    main()