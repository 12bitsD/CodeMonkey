
const BASE_URL = 'http://localhost:3000/api';

async function testGraphApi() {
    console.log('🧪 Starting Graph API Integration Test...');

    const planId = 'p_demo';
    const nodeId = 'n1';

    // 1. Test GET Graph
    console.log(`\n[TEST] GET /plans/${planId}/graph`);
    try {
        const res = await fetch(`${BASE_URL}/plans/${planId}/graph`);
        const json = await res.json();
        
        if (json.success && json.data.nodes && json.data.edges) {
            console.log('✅ GET Graph Passed');
            console.log(`   Received ${json.data.nodes.length} nodes, ${json.data.edges.length} edges`);
        } else {
            console.error('❌ GET Graph Failed', json);
            process.exit(1);
        }
    } catch (e) {
        console.error('❌ GET Graph Error', e);
        process.exit(1);
    }

    // 2. Test Update Status
    console.log(`\n[TEST] PUT /plans/${planId}/nodes/${nodeId}/status`);
    try {
        const res = await fetch(`${BASE_URL}/plans/${planId}/nodes/${nodeId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'learned' })
        });
        const json = await res.json();

        if (json.success && json.data.status === 'learned') {
            console.log('✅ Update Status Passed');
            console.log(`   Progress updated: ${json.data.plan.progress}/${json.data.plan.total}`);
        } else {
            console.error('❌ Update Status Failed', json);
            process.exit(1);
        }
    } catch (e) {
        console.error('❌ Update Status Error', e);
        process.exit(1);
    }

    // 3. Test Update Position
    console.log(`\n[TEST] PUT /plans/${planId}/nodes/${nodeId}/position`);
    try {
        const res = await fetch(`${BASE_URL}/plans/${planId}/nodes/${nodeId}/position`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: 50, y: 50 })
        });
        const json = await res.json();

        if (json.success && json.data.x === 50) {
            console.log('✅ Update Position Passed');
        } else {
            console.error('❌ Update Position Failed', json);
            process.exit(1);
        }
    } catch (e) {
        console.error('❌ Update Position Error', e);
        process.exit(1);
    }

    console.log('\n🎉 All Graph API Tests Passed!');
}

testGraphApi();
