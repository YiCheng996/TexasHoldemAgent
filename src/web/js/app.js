// 游戏状态
let gameState = {
    gameId: null,
    phase: 'WAITING',
    potSize: 0,
    communityCards: [],
    currentPlayer: null,
    players: [],
    minRaise: 0,
    maxRaise: 0
};

// WebSocket连接
let ws = null;

// DOM元素
const elements = {
    gameId: document.getElementById('game-id'),
    gamePhase: document.getElementById('game-phase'),
    potSize: document.getElementById('pot-size'),
    minRaise: document.getElementById('min-raise'),
    currentPlayer: document.getElementById('current-player'),
    potDisplay: document.getElementById('pot-display'),
    playersContainer: document.getElementById('players-container'),
    actionPanel: document.getElementById('action-panel'),
    statusMessage: document.getElementById('status-message'),
    raiseDialog: document.getElementById('raise-dialog'),
    raiseAmount: document.getElementById('raise-amount')
};

// 检查DOM元素是否存在
function checkDOMElements() {
    console.log('检查DOM元素:');
    for (const [key, element] of Object.entries(elements)) {
        console.log(`${key}: ${element ? '已找到' : '未找到'}`);
        if (!element) {
            console.error(`未找到元素: ${key}`);
        }
    }
}

// 初始化游戏
async function initGame() {
    console.log('开始初始化游戏...');
    checkDOMElements();
    
    try {
        const response = await fetch('/api/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                num_players: 5,
                initial_stack: 1000,
                small_blind: 10
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('游戏创建响应:', data);
        
        if (data.success) {
            // 更新游戏状态
            gameState = {
                gameId: data.game_id,
                phase: data.state.phase,
                potSize: data.state.pot_size,
                communityCards: data.state.community_cards,
                currentPlayer: data.state.current_player,
                minRaise: data.state.min_raise,
                maxRaise: data.state.max_raise,
                players: data.state.players.map(player => ({
                    ...player,
                    currentBet: player.current_bet,
                    isActive: player.is_active,
                    isAllIn: player.is_all_in
                }))
            };
            
            // 连接WebSocket
            connectWebSocket(data.game_id);
            
            // 更新UI
            updateUI();
            console.log('游戏初始化完成，当前状态:', gameState);
        } else {
            throw new Error('游戏创建失败');
        }
    } catch (error) {
        console.error('初始化游戏失败:', error);
        showError('初始化游戏失败，请刷新页面重试');
    }
}

// 连接WebSocket
function connectWebSocket(gameId) {
    ws = new WebSocket(`ws://${window.location.host}/ws/${gameId}`);
    
    ws.onopen = () => {
        console.log('WebSocket连接已建立');
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('收到WebSocket消息:', message);
        handleWebSocketMessage(message);
    };
    
    ws.onclose = () => {
        console.log('WebSocket连接已关闭');
        showError('与服务器的连接已断开,请刷新页面重试');
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        showError('连接出错,请刷新页面重试');
    };
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log('收到WebSocket消息:', message);
    
    // 处理心跳消息
    if (message === 'ping') {
        ws.send('pong');
        return;
    }
    
    // 更新游戏状态
    if (message.phase !== undefined) {
        console.log('更新游戏状态:', message);
        gameState = {
            ...gameState,
            ...message,
            phase: message.phase,
            potSize: message.pot_size,
            communityCards: message.community_cards,
            currentPlayer: message.current_player,
            minRaise: message.min_raise,
            maxRaise: message.max_raise,
            players: message.players.map(player => ({
                ...player,
                currentBet: player.current_bet,
                isActive: player.is_active,
                isAllIn: player.is_all_in
            }))
        };
        updateUI();
        return;
    }
    
    // 处理其他类型的消息
    if (message.type) {
        switch (message.type) {
            case 'error':
                showError(message.message || '发生错误');
                    break;
            case 'game_result':
                showGameResult(message.data);
                    break;
                default:
                console.log('未知消息类型:', message.type);
        }
    }
}

// 更新UI
function updateUI() {
    console.log('更新UI，当前游戏状态:', gameState);
    
    // 更新游戏信息
    elements.gameId.textContent = `游戏ID: ${gameState.gameId || '-'}`;
    elements.gamePhase.textContent = `阶段: ${getPhaseText(gameState.phase)}`;
    elements.potSize.textContent = `底池: ${gameState.potSize || 0}`;
    elements.minRaise.textContent = `最小加注: ${gameState.minRaise || 0}`;
    elements.currentPlayer.textContent = `当前行动: ${
        gameState.currentPlayer === 'player_0' ? '我' :
        gameState.currentPlayer ? 'AI玩家 ' + gameState.currentPlayer.slice(-1) : '-'
    }`;
    
    // 更新底池显示
    elements.potDisplay.textContent = `底池: ${gameState.potSize || 0}`;
    
    // 更新公共牌
    updateCommunityCards();
    
    // 更新玩家区域
    updatePlayers();
    
    // 更新操作面板
    updateActionPanel();
    
    // 更新状态消息
    elements.statusMessage.textContent = getStatusMessage();
    elements.statusMessage.style.display = 'block';
}

// 更新公共牌
function updateCommunityCards() {
    const cards = gameState.communityCards || [];
    const positions = ['flop1', 'flop2', 'flop3', 'turn', 'river'];
    
    positions.forEach((pos, index) => {
        const container = document.getElementById(pos);
        if (container) {
            container.innerHTML = cards[index] ? createCardHTML(cards[index]) : '<div class="card-placeholder">?</div>';
        }
    });
}

// 更新玩家区域
function updatePlayers() {
    elements.playersContainer.innerHTML = '';
    
    if (!gameState.players || gameState.players.length === 0) {
        console.log('没有玩家数据');
                return;
            }
            
    console.log('更新玩家显示:', gameState.players);
    
    // 计算每个玩家的位置
    const positions = calculatePlayerPositions(gameState.players.length);
    
    gameState.players.forEach((player, index) => {
        const seat = document.createElement('div');
        seat.className = `player-seat ${player.id === gameState.current_player ? 'active' : ''} ${!player.is_active ? 'inactive' : ''}`;
        
        // 设置位置样式
        const position = positions[index];
        seat.style.cssText = position;
        
        // 创建玩家信息HTML
        seat.innerHTML = `
            <div class="player-info">
                <div class="player-name">${player.id === 'player_0' ? '我' : 'AI玩家 ' + player.id.slice(-1)}</div>
                <div class="player-chips">筹码: ${player.chips}</div>
                <div class="player-bet">当前下注: ${player.current_bet || 0}</div>
                ${player.is_all_in ? '<div class="player-all-in">全下</div>' : ''}
            </div>
            <div class="cards">
                ${player.id === 'player_0' && player.cards ? 
                    player.cards.map(card => createCardHTML(card)).join('') :
                    '<div class="card-placeholder">?</div><div class="card-placeholder">?</div>'
                }
            </div>
        `;
        
        elements.playersContainer.appendChild(seat);
    });
}

        // 计算玩家位置
function calculatePlayerPositions(numPlayers) {
    const positions = [];
    
    // 固定位置布局
    const layoutPositions = [
        // 最右侧（AI1的位置）
        'right: 2%; top: 40%; transform: translate(0, -40%);',
        // 中右侧（AI2的位置）
        'right: 25%; top: 80%; transform: translate(0, -40%);',
        // 中间（AI3的位置）
        'right: 45%; top: 80%; transform: translate(0, -40%);',
        // 中左侧（AI4的位置）
        'right: 65%; top: 80%; transform: translate(0, -40%);',
        // 最左侧（人类玩家的位置）
        'left: 2%; top: 40%; transform: translate(0, -40%);'
    ];
    
    // 根据玩家位置排序
    const orderedPlayers = gameState.players.sort((a, b) => a.position - b.position);
    
    // 分配位置
    orderedPlayers.forEach((player, index) => {
        positions[index] = layoutPositions[index];
    });
    
    return positions;
}

// 更新操作面板
function updateActionPanel() {
    const isPlayerTurn = gameState.currentPlayer === 'player_0';
    elements.actionPanel.style.display = isPlayerTurn ? 'flex' : 'none';
    
    if (isPlayerTurn) {
        const currentPlayer = gameState.players.find(p => p.id === 'player_0');
        const maxBet = Math.max(...gameState.players.map(p => p.currentBet));
        
        // 更新按钮状态
        const checkButton = elements.actionPanel.querySelector('.btn-check');
        const callButton = elements.actionPanel.querySelector('.btn-call');
        const raiseButton = elements.actionPanel.querySelector('.btn-raise');
        
        checkButton.disabled = maxBet > currentPlayer.currentBet;
        callButton.disabled = maxBet === currentPlayer.currentBet;
        raiseButton.disabled = currentPlayer.chips <= maxBet - currentPlayer.currentBet;
    }
}

// 处理玩家动作
function handleAction(action) {
    if (!ws) {
        showError('网络连接已断开，请刷新页面重试');
        return;
    }
    
    try {
        const message = {
            player_id: 'player_0',
            action: action,
            amount: action === 'RAISE' ? parseInt(elements.raiseAmount.value) : 0
        };
        
        console.log('发送动作:', message);
        ws.send(JSON.stringify(message));
    } catch (error) {
        console.error('发送动作失败:', error);
        showError('发送动作失败，请重试');
    }
}

// 显示加注对话框
function showRaiseDialog() {
    const currentPlayer = gameState.players.find(p => p.id === 'player_0');
    if (!currentPlayer) {
        showError('无法获取玩家信息');
        return;
    }
    
    // 获取当前最大注额
    const maxBet = Math.max(...gameState.players.map(p => p.currentBet));
    // 计算最小加注额（当前最大注的两倍）
    const minRaiseAmount = Math.max(gameState.minRaise, maxBet * 2);
    
    // 设置加注范围
    elements.raiseAmount.min = minRaiseAmount;
    elements.raiseAmount.max = currentPlayer.chips;
    elements.raiseAmount.value = minRaiseAmount;
    
    // 更新对话框显示
    const raiseContent = elements.raiseDialog.querySelector('.raise-content');
    if (raiseContent) {
        raiseContent.innerHTML = `
            <h3>请输入加注金额</h3>
            <div class="raise-info">
                <p>最小加注: ${minRaiseAmount}</p>
                <p>最大加注: ${currentPlayer.chips}</p>
                <p>当前筹码: ${currentPlayer.chips}</p>
            </div>
            <input type="number" id="raise-amount" 
                min="${minRaiseAmount}" 
                max="${currentPlayer.chips}" 
                value="${minRaiseAmount}"
                step="1">
            <div class="raise-buttons">
                <button onclick="handleRaise()">确认</button>
                <button onclick="hideRaiseDialog()">取消</button>
            </div>
        `;
    }
    
    elements.raiseDialog.style.display = 'flex';
    
    // 聚焦到输入框
    const raiseAmount = document.getElementById('raise-amount');
    if (raiseAmount) {
        raiseAmount.focus();
        raiseAmount.select();
    }
}

// 隐藏加注对话框
function hideRaiseDialog() {
    elements.raiseDialog.style.display = 'none';
}

// 处理加注
function handleRaise() {
    const amount = parseInt(elements.raiseAmount.value);
    const currentPlayer = gameState.players.find(p => p.id === 'player_0');
    
                if (!currentPlayer) {
        showError('无法获取玩家信息');
        return;
    }
    
    // 验证加注金额
    if (isNaN(amount)) {
        showError('请输入有效的加注金额');
        return;
    }
    
    if (amount > currentPlayer.chips) {
        showError('加注金额不能超过当前筹码');
                        return;
    }
    
    if (amount < gameState.minRaise) {
        showError(`加注金额不能小于最小加注额 ${gameState.minRaise}`);
                return;
            }
    
    if (gameState.maxRaise && amount > gameState.maxRaise) {
        showError(`加注金额不能超过最大加注额 ${gameState.maxRaise}`);
                return;
            }
    
    handleAction('RAISE');
    hideRaiseDialog();
}

// 显示错误消息
function showError(message) {
    elements.statusMessage.style.display = 'block';
    elements.statusMessage.textContent = message;
}

// 显示游戏结果
function showGameResult(result) {
    elements.statusMessage.style.display = 'block';
    elements.statusMessage.textContent = `游戏结束! 赢家: ${
        result.winner === 'player_0' ? '我' : 'AI玩家 ' + result.winner.slice(-1)
    }, 赢得筹码: ${result.pot}`;
}

// 工具函数
function getPhaseText(phase) {
    const phaseMap = {
        'WAITING': '等待开始',
        'PRE_FLOP': '翻牌前',
        'FLOP': '翻牌',
        'TURN': '转牌',
        'RIVER': '河牌',
        'SHOWDOWN': '摊牌',
        'FINISHED': '结束'
    };
    return phaseMap[phase] || phase;
}

function getStatusMessage() {
    if (!gameState.phase || gameState.phase === 'WAITING') {
        return '等待游戏开始...';
    }
    
    if (gameState.phase === 'FINISHED') {
        return '游戏已结束';
    }
    
    if (gameState.currentPlayer === 'player_0') {
        return '轮到您行动了';
    }
    
    return gameState.currentPlayer ? 
        `等待AI玩家 ${gameState.currentPlayer.slice(-1)} 行动` :
        '等待其他玩家行动...';
}

function createCardHTML(card) {
    if (!card) return '<div class="card-placeholder">?</div>';
    
    const rank = card.slice(0, -1);
    const suit = card.slice(-1);
    const suitClass = {
        '♥': 'hearts',
        '♦': 'diamonds',
        '♠': 'spades',
        '♣': 'clubs'
    }[suit];
    
    return `
        <div class="card">
            <div class="card-rank">${rank}</div>
            <div class="card-suit ${suitClass}">${suit}</div>
        </div>
    `;
}

// 初始化游戏
document.addEventListener('DOMContentLoaded', initGame); 