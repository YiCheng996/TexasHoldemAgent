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
            body: JSON.stringify({})
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
        console.log('消息中的玩家数据:', message.players);
        
        // 先更新游戏状态
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
        
        // 如果游戏阶段是FINISHED，显示结算弹窗并立即更新UI
        if (message.phase === 'FINISHED') {
            console.log('游戏结束，检查游戏结果:', message.game_result);
            updateUI();  // 先更新UI以反映最终状态
            
            if (message.game_result) {
                console.log('显示游戏结果:', message.game_result);
                showGameResult(message.game_result);
            } else {
                console.error('游戏结束但没有结果数据');
            }
            return;
        }
        
        // 更新UI
        updateUI();
        
        // 检查是否有table_talk消息
        if (message.table_talk && message.table_talk.message) {
            // 获取发送消息的玩家ID
            const actionPlayer = message.players.find(p => p.last_action);
            console.log('执行动作的玩家:', actionPlayer);
            
            if (actionPlayer && actionPlayer.id.startsWith('ai_')) {
                console.log('显示AI消息:', actionPlayer.id, message.table_talk.message);
                // 短暂延迟以确保DOM已更新
                setTimeout(() => {
                    showPlayerMessage(actionPlayer.id, message.table_talk.message);
                }, 100);
            }
        }
        
        return;
    }
    
    // 处理其他类型的消息
    if (message.type) {
        switch (message.type) {
            case 'error':
                showError(message.message || '发生错误');
                break;
            case 'game_result':
                console.log('收到游戏结果消息:', message.data);
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
    elements.currentPlayer.textContent = gameState.phase === 'FINISHED' ? 
        '游戏已结束' : 
        `当前行动: ${
            gameState.currentPlayer === 'player_0' ? '我' :
            gameState.currentPlayer ? getPlayerDisplayName(gameState.currentPlayer) : '-'
        }`;
    
    // 更新底池显示
    elements.potDisplay.textContent = `底池: ${gameState.potSize || 0}`;
    
    // 更新公共牌
    updateCommunityCards();
    
    // 更新玩家区域
    updatePlayers();
    
    // 更新操作面板（在FINISHED状态下隐藏）
    if (gameState.phase === 'FINISHED') {
        elements.actionPanel.style.display = 'none';
    } else {
        updateActionPanel();
    }
    
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
        seat.className = `player-seat ${player.id === gameState.currentPlayer ? 'active' : ''} ${!player.isActive ? 'inactive' : ''}`;
        
        // 设置位置样式
        const position = positions[index];
        seat.style.cssText = position;
        
        // 设置data-player-id属性
        seat.setAttribute('data-player-id', player.id);
        console.log(`创建玩家座位，ID: ${player.id}, 位置: ${position}`);
        
        // 创建玩家信息HTML
        seat.innerHTML = `
            <div class="player-info" data-player-id="${player.id}">
                <div class="player-name">${player.id === 'player_0' ? '我' : getPlayerDisplayName(player.id)}</div>
                <div class="player-chips">筹码: ${player.chips}</div>
                <div class="player-bet">当前下注: ${player.current_bet || 0}</div>
                ${player.is_all_in ? '<div class="player-all-in">全下</div>' : ''}
            </div>
            <div class="cards">
                ${player.cards && player.cards.length > 0 ? 
                    player.cards.map(card => createCardHTML(card)).join('') :
                    '<div class="card-placeholder">?</div><div class="card-placeholder">?</div>'
                }
            </div>
        `;
        
        elements.playersContainer.appendChild(seat);
        
        // 验证座位元素是否正确创建
        const createdSeat = elements.playersContainer.querySelector(`[data-player-id="${player.id}"]`);
        console.log(`验证玩家 ${player.id} 的座位元素:`, createdSeat ? '成功' : '失败');
    });
    
    // 验证所有玩家座位
    const allSeats = elements.playersContainer.querySelectorAll('.player-seat');
    console.log('所有玩家座位:', allSeats.length);
    allSeats.forEach(seat => {
        const id = seat.getAttribute('data-player-id');
        console.log(`座位ID: ${id}`);
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
async function handleAction(actionType, amount = 0) {
    console.log('发送动作:', actionType, '金额:', amount);
    
    if (gameState.phase === 'FINISHED') {
        showError('游戏已结束，请开始新的一局');
        return;
    }
    
    try {
        const response = await fetch(`/api/games/${gameState.gameId}/action`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                player_id: 'player_0',
                action_type: actionType,
                amount: amount
            })
        });
        
        // 获取响应文本
        const responseText = await response.text();
        console.log('服务器响应:', responseText);
        
        // 尝试解析JSON
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('解析响应JSON失败:', e);
            throw new Error(`服务器响应格式错误: ${responseText}`);
        }
        
        if (!response.ok) {
            // 如果响应不成功，抛出错误
            const errorMessage = data?.detail || data?.message || '动作执行失败';
            throw new Error(errorMessage);
        }
        
        // 验证响应数据的完整性
        if (!data || typeof data !== 'object') {
            console.error('无效的响应数据:', data);
            throw new Error('服务器返回的数据无效');
        }
        
        // 验证必要字段
        if (data.phase === undefined) {
            console.error('响应数据缺少phase字段:', data);
            throw new Error('服务器返回的数据不完整');
        }
        
        // 更新游戏状态
        gameState = {
            ...gameState,
            phase: data.phase,
            potSize: data.pot_size,
            communityCards: data.community_cards,
            currentPlayer: data.current_player,
            minRaise: data.min_raise,
            maxRaise: data.max_raise,
            players: data.players.map(player => ({
                ...player,
                currentBet: player.current_bet,
                isActive: player.is_active,
                isAllIn: player.is_all_in
            }))
        };
        
        // 如果游戏结束，显示结果
        if (data.phase === 'FINISHED' && data.game_result) {
            showGameResult(data.game_result);
        }
        
        updateUI();
        
    } catch (error) {
        console.error('执行动作失败:', error);
        showError(error.message || '执行动作时发生错误');
    }
}

// 显示加注对话框
function showRaiseDialog() {
    const currentPlayer = gameState.players.find(p => p.id === 'player_0');
    if (!currentPlayer) {
        showError('无法获取玩家信息');
        return;
    }
    
    // 计算最小加注额
    const maxBet = Math.max(...gameState.players.map(p => p.currentBet));
    const minRaiseAmount = Math.max(
        gameState.minRaise,
        maxBet * 2  // 确保最小加注至少是当前最大注的两倍
    );
    
    // 更新输入框限制
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
    // 获取输入框元素
    const raiseAmountInput = document.getElementById('raise-amount');
    const amount = parseInt(raiseAmountInput.value);  // 使用新获取的输入框元素
    
    console.log('加注金额:', amount); // 添加日志
    
    const currentPlayer = gameState.players.find(p => p.id === 'player_0');
    if (!currentPlayer) {
        showError('无法获取玩家信息');
        return;
    }
    
    // 验证加注金额
    if (isNaN(amount) || amount <= 0) {
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
    
    // 发送加注动作
    handleAction('RAISE', amount);
    hideRaiseDialog();
}

// 显示错误消息
function showError(message) {
    elements.statusMessage.style.display = 'block';
    elements.statusMessage.textContent = message;
}

// 首先定义所有需要的函数
function getHandRankText(handRank) {
    if (!handRank) return '';
    
    const rankMap = {
        'HIGH_CARD': '高牌',
        'PAIR': '一对',
        'TWO_PAIR': '两对',
        'THREE_OF_A_KIND': '三条',
        'STRAIGHT': '顺子',
        'FLUSH': '同花',
        'FULL_HOUSE': '葫芦',
        'FOUR_OF_A_KIND': '四条',
        'STRAIGHT_FLUSH': '同花顺',
        'ROYAL_FLUSH': '皇家同花顺',
        'WINNER_BY_FOLD': '其他玩家弃牌'
    };
    
    return rankMap[handRank] || handRank;
}

// 显示游戏结果
function showGameResult(result) {
    try {
        console.log('显示游戏结果:', result);
        
        if (!result) {
            console.error('游戏结果为空');
            return;
        }
        
        const resultDialog = document.getElementById('result-dialog');
        const resultMessage = document.getElementById('result-message');
        
        if (!resultDialog || !resultMessage) {
            console.error('找不到结果弹窗元素:', {
                resultDialog: !!resultDialog,
                resultMessage: !!resultMessage
            });
            return;
        }
        
        // 检查结果数据完整性
        if (!result.winner_id) {
            console.error('游戏结果缺少获胜者ID:', result);
            return;
        }
        
        // 构建结果消息
        let message = `<div class="game-result">`;
        
        // 显示获胜者
        const winnerId = result.winner_id;
        const winnerName = winnerId === 'player_0' ? '我' : getPlayerDisplayName(winnerId);
        message += `<h3>${winnerName} 获胜!</h3>`;
        message += `<p>赢得筹码: ${result.pot_amount}</p>`;
        
        // 显示公共牌（如果有）
        if (result.community_cards && result.community_cards.length > 0) {
            message += `<div class="community-cards">
                <h4>公共牌</h4>
                <div class="cards">
                    ${result.community_cards.map(card => createCardHTML(card)).join('')}
                </div>
            </div>`;
        }
        
        // 显示摊牌数据
        if (result.showdown_data && result.showdown_data.length > 0) {
            message += `<div class="showdown-data">
                <h4>玩家手牌</h4>`;
                
            // 遍历每个玩家的摊牌数据
            message += result.showdown_data.map(player => {
                if (!player || !player.player_id) {
                    console.error('摊牌数据中有无效玩家:', player);
                    return '';
                }
                
                return `
                <div class="player-hand ${player.is_winner ? 'winner' : ''}">
                    <div class="player-info">
                        <span>${player.player_id === 'player_0' ? '我' : getPlayerDisplayName(player.player_id)}</span>
                        ${player.hand_rank === 'WINNER_BY_FOLD' ? 
                            '<span class="hand-rank">(因其他玩家弃牌获胜)</span>' : 
                            `<span class="hand-rank">(${getHandRankText(player.hand_rank)})</span>`
                        }
                    </div>
                    <div class="cards">
                        ${player.hole_cards && player.hole_cards.length > 0 ? 
                            player.hole_cards.map(card => createCardHTML(card)).join('') : 
                            '<div class="card-placeholder">无牌</div>'
                        }
                    </div>
                </div>
            `;
            }).join('');
            
            message += `</div>`;
        }
        
        message += `</div>`;
        
        console.log('构建的结果消息HTML:', message);
        
        // 设置弹窗内容和显示
        resultMessage.innerHTML = message;
        resultDialog.style.display = 'flex';
        console.log('游戏结果弹窗已显示');
        
    } catch (error) {
        console.error('显示游戏结果时出错:', error);
        showError('显示游戏结果时出错: ' + error.message);
    }
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
        `等待${getPlayerDisplayName(gameState.currentPlayer)}行动` :
        '等待其他玩家行动...';
}

// 创建卡牌HTML
function createCardHTML(card) {
    try {
        if (!card) {
            console.error('卡牌数据为空');
            return '<div class="card card-unknown">?</div>';
        }
        
        // 处理不同的卡牌格式
        let suit, rank;
        
        if (typeof card === 'string') {
            // 如果是字符串格式 (例如 "AS" 或 "A♠")
            rank = card.charAt(0);
            
            // 检查是否为Unicode花色符号
            if (card.length > 1) {
                if (['♠', '♥', '♦', '♣'].includes(card.charAt(1))) {
                    suit = card.charAt(1);
                } else {
                    suit = card.charAt(1);
                }
            } else {
                suit = '?';
            }
        } else if (card.suit !== undefined && card.rank !== undefined) {
            // 如果是对象格式 (例如 {suit: "S", rank: "A"})
            suit = card.suit;
            rank = card.rank;
        } else if (card.to_string) {
            // 如果有to_string方法
            const cardStr = card.to_string();
            rank = cardStr.charAt(0);
            suit = cardStr.charAt(1);
        } else {
            console.error('无法识别的卡牌格式:', card);
            return '<div class="card card-unknown">?</div>';
        }
        
        // 处理长度为2以上的牌面值（如"10"）
        if (rank === '1' && typeof card === 'string' && card.length >= 3) {
            rank = '10';
            // 调整花色的位置
            if (['♠', '♥', '♦', '♣'].includes(card.charAt(2))) {
                suit = card.charAt(2);
            } else {
                suit = card.charAt(2);
            }
        }
        
        // 转换花色为符号（如果不是已经是符号）
        let suitSymbol;
        if (['♠', '♥', '♦', '♣'].includes(suit)) {
            suitSymbol = suit; // 已经是Unicode符号，直接使用
        } else {
            // 如果是字母，转换为符号
            switch (suit.toUpperCase()) {
                case 'S': suitSymbol = '♠'; break;
                case 'H': suitSymbol = '♥'; break;
                case 'D': suitSymbol = '♦'; break;
                case 'C': suitSymbol = '♣'; break;
                default: suitSymbol = suit;
            }
        }
        
        // 转换数字牌为正确显示
        let rankDisplay;
        switch (rank.toUpperCase()) {
            case 'T': rankDisplay = '10'; break;
            case 'J': rankDisplay = 'J'; break;
            case 'Q': rankDisplay = 'Q'; break;
            case 'K': rankDisplay = 'K'; break;
            case 'A': rankDisplay = 'A'; break;
            default: rankDisplay = rank;
        }
        
        // 确定花色颜色
        const isRed = suitSymbol === '♥' || suitSymbol === '♦';
        const colorClass = isRed ? 'card-red' : 'card-black';
        
        // 添加花色特定类，用于CSS样式
        let suitClass = '';
        if (suitSymbol === '♠') suitClass = 'spades';
        else if (suitSymbol === '♥') suitClass = 'hearts';
        else if (suitSymbol === '♦') suitClass = 'diamonds';
        else if (suitSymbol === '♣') suitClass = 'clubs';
        
        // 返回卡牌HTML，将花色添加到data-suit属性中
        return `<div class="card ${colorClass}">
            <div class="card-rank" data-suit="${suitSymbol}">${rankDisplay}</div>
            <div class="card-suit ${suitClass}">${suitSymbol}</div>
        </div>`;
    } catch (error) {
        console.error('创建卡牌HTML时出错:', error, '卡牌数据:', card);
        return '<div class="card card-unknown">?</div>';
    }
}

// 初始化游戏
document.addEventListener('DOMContentLoaded', initGame);

// 开始新游戏
async function startNewGame() {
    try {
        // 检查游戏状态
        if (gameState.phase !== 'FINISHED') {
            showError('只能在游戏结束后开始新游戏');
            return;
        }

        const response = await fetch(`/api/games/${gameState.gameId}/new_game`, {
            method: 'POST'
        });
        
        // 获取响应文本
        const responseText = await response.text();
        console.log('服务器响应:', responseText);
        
        // 尝试解析JSON
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('解析响应JSON失败:', e);
            throw new Error(`服务器响应格式错误: ${responseText}`);
        }
        
        if (!response.ok) {
            const error = data?.detail || data?.message || '开始新游戏失败';
            throw new Error(error);
        }
        
        // 更新游戏状态
        if (data.state) {
            gameState = {
                ...gameState,
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
            
            // 隐藏结果弹窗
            const resultDialog = document.getElementById('result-dialog');
            if (resultDialog) {
                resultDialog.style.display = 'none';
            }
            
            // 更新UI
            updateUI();
            console.log('新游戏已开始，当前状态:', gameState);
        }
        
    } catch (error) {
        console.error('开始新游戏失败:', error);
        showError(error.message);
    }
}

// 修改showPlayerMessage函数
function showPlayerMessage(playerId, message) {
    console.log('尝试显示玩家消息:', playerId, message);
    
    // 直接查找玩家座位
    try {
        let playerSeat = document.querySelector(`.player-seat[data-player-id="${playerId}"]`);
        console.log('查找到的玩家座位元素:', playerSeat);
        
        if (!playerSeat) {
            console.error(`找不到玩家座位: ${playerId}`);
            // 尝试重新查找
            setTimeout(() => {
                try {
                    // 首先尝试直接查找
                    playerSeat = document.querySelector(`.player-seat[data-player-id="${playerId}"]`);
                    console.log('重试查找到的玩家座位元素:', playerSeat);
                    
                    if (playerSeat) {
                        console.log('重试成功找到玩家座位');
                        showPlayerMessageImpl(playerSeat, message);
                    } else {
                        // 如果还是找不到，输出所有座位信息以便调试
                        const allSeats = document.querySelectorAll('.player-seat');
                        console.log('所有玩家座位元素:', allSeats);
                        allSeats.forEach(seat => {
                            const id = seat.getAttribute('data-player-id');
                            console.log(`座位元素:`, {
                                id: id,
                                classList: seat.className,
                                html: seat.innerHTML
                            });
                            if (id === playerId) {
                                console.log('通过遍历找到玩家座位');
                                showPlayerMessageImpl(seat, message);
                                return;
                            }
                        });
                        
                        if (!playerSeat) {
                            console.error('重试仍然找不到玩家座位，当前DOM结构:', document.querySelector('#players-container').innerHTML);
                        }
                    }
                } catch (error) {
                    console.error('重试查找玩家座位时出错:', error);
                }
            }, 100);
            return;
        }

        showPlayerMessageImpl(playerSeat, message);
    } catch (error) {
        console.error('查找玩家座位时出错:', error);
    }
}

// 添加实际显示消息的辅助函数
function showPlayerMessageImpl(playerSeat, message) {
    // 移除现有的对话气泡
    const existingBubble = playerSeat.querySelector('.player-speech-bubble');
    if (existingBubble) {
        existingBubble.remove();
    }

    // 创建新的对话气泡
    const bubble = document.createElement('div');
    bubble.className = 'player-speech-bubble';
    bubble.innerHTML = `<div class="message-text">${message}</div>`;

    // 添加到玩家座位
    playerSeat.appendChild(bubble);
    console.log('对话气泡已添加到玩家座位');

    // 添加active类以触发动画
    requestAnimationFrame(() => {
        bubble.classList.add('active');
        console.log('对话气泡动画已激活');
    });

    // 5秒后移除
    setTimeout(() => {
        bubble.classList.remove('active');
        setTimeout(() => bubble.remove(), 300);
        console.log('对话气泡已移除');
    }, 5000);
}

// 修改updatePlayersDisplay函数
function updatePlayersDisplay() {
    const playersContainer = document.getElementById('players-container');
    if (!playersContainer) {
        console.error('找不到players-container元素');
        return;
    }
    
    playersContainer.innerHTML = '';
    
    // 计算玩家位置
    const positions = [
        'bottom-center',  // 玩家自己的位置
        'right',         // AI 1的位置
        'left',          // AI 2的位置
    ];
    
    // 确保gameState.players存在且是数组
    if (!Array.isArray(gameState.players)) {
        console.error('gameState.players不是数组:', gameState.players);
        return;
    }
    
    console.log('更新玩家显示，当前玩家数据:', gameState.players);
    
    gameState.players.forEach((player, index) => {
        const playerDiv = document.createElement('div');
        playerDiv.className = `player-seat position-${positions[index]}`;
        playerDiv.setAttribute('data-player-id', player.id);  // 添加到外层div
        
        // 添加当前行动玩家的高亮效果
        if (player.id === gameState.currentPlayer) {
            playerDiv.classList.add('active');
            console.log(`设置玩家 ${player.id} 为当前行动玩家`);
        }
        
        // 添加玩家是否激活的状态
        if (!player.isActive) {
            playerDiv.classList.add('inactive');
        }
        
        // 构建玩家信息HTML
        playerDiv.innerHTML = `
            <div class="player-info">
                <div class="player-name">${player.id === 'player_0' ? '我' : getPlayerDisplayName(player.id)}</div>
                <div class="player-chips">筹码: ${player.chips}</div>
                ${player.currentBet > 0 ? `<div class="player-bet">当前下注: ${player.currentBet}</div>` : ''}
                ${player.isAllIn ? '<div class="player-all-in">全下</div>' : ''}
            </div>
            <div class="player-cards">
                ${player.cards ? player.cards.map(card => createCardHTML(card)).join('') : ''}
            </div>
        `;
        
        playersContainer.appendChild(playerDiv);
        console.log(`已添加玩家 ${player.id} 的座位元素，data-player-id=${player.id}，位置=${positions[index]}`);
    });
    
    // 验证所有玩家座位是否正确创建
    const allSeats = document.querySelectorAll('.player-seat');
    console.log('创建完成后的所有玩家座位:', allSeats);
    allSeats.forEach(seat => {
        console.log('座位ID:', seat.getAttribute('data-player-id'));
    });
}

// 更新游戏状态的函数
function updateGameState(data) {
    console.log('收到游戏状态更新:', data);
    
    if (data.state) {
        gameState = {
            ...gameState,
            phase: data.state.phase,
            potSize: data.state.pot_size,
            communityCards: data.state.community_cards,
            currentPlayer: data.state.current_player,  // 确保正确更新当前玩家
            minRaise: data.state.min_raise,
            maxRaise: data.state.max_raise,
            players: data.state.players.map(player => ({
                ...player,
                currentBet: player.current_bet,
                isActive: player.is_active,
                isAllIn: player.is_all_in
            }))
        };
        
        // 如果游戏结束，显示结果
        if (data.state.phase === 'FINISHED' && data.state.game_result) {
            console.log('游戏结束，显示结果:', data.state.game_result);
            showGameResult(data.state.game_result);
        }
        
        updateUI();
    } else {
        // 直接处理没有state包装的数据
        gameState = {
            ...gameState,
            phase: data.phase,
            potSize: data.pot_size,
            communityCards: data.community_cards,
            currentPlayer: data.current_player,
            minRaise: data.min_raise,
            maxRaise: data.max_raise,
            players: data.players.map(player => ({
                ...player,
                currentBet: player.current_bet,
                isActive: player.is_active,
                isAllIn: player.is_all_in
            }))
        };
        
        // 如果游戏结束，显示结果
        if (data.phase === 'FINISHED' && data.game_result) {
            console.log('游戏结束，显示结果:', data.game_result);
            showGameResult(data.game_result);
        }
        
        updateUI();
    }
}

// 添加一个新的辅助函数来获取玩家显示名称
function getPlayerDisplayName(playerId) {
    if (playerId === 'player_0') return '我';
    
    // 查找玩家数据
    const player = gameState.players.find(p => p.id === playerId);
    if (!player) return `AI玩家 ${playerId.slice(-1)}`;  // 回退到默认显示
    
    // 如果有模型名称，使用它
    if (player.model_name) {
        // 提取模型名称的最后一部分（例如从"openai/glm-4-air"提取"glm-4-air"）
        const modelName = player.model_name.split('/').pop();
        return modelName;
    }
    
    // 如果没有模型名称，使用默认显示
    return `AI玩家 ${playerId.slice(-1)}`;
} 