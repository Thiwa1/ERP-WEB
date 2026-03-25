import re

with open('templates/index.html', 'r') as f:
    content = f.read()

new_header = '''<!-- Win11 Style Dashboard Overview -->
<div class="mb-4 bg-white p-4 rounded-4 shadow-sm border border-light">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="fw-bold mb-0 text-dark" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">Dashboard Overview</h4>
        <button class="btn btn-sm btn-link text-decoration-none text-muted fw-semibold">All apps <i class="fas fa-chevron-right ms-1 small"></i></button>
    </div>

    <div class="row g-3 mb-4">
        <!-- Dashboard Windows 11 App Icons -->
        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="/pos" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light">
                <div class="bg-primary bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-cash-register fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">POS</span>
            </a>
        </div>

        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="/inventory_reports" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light">
                <div class="bg-success bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-boxes fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">Inventory</span>
            </a>
        </div>

        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="/bank_reconciliation" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light">
                <div class="bg-warning bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-university fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">Banking</span>
            </a>
        </div>

        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="/profit_loss" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light">
                <div class="bg-danger bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-chart-pie fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">Reports</span>
            </a>
        </div>

        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="/customer_receipt" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light">
                <div class="bg-info bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-receipt fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">Receipts</span>
            </a>
        </div>

        <div class="col-4 col-sm-3 col-md-2 text-center">
            <a href="#" class="text-decoration-none d-block p-3 rounded-4 transition-all hover-lift bg-light shadow-sm border border-light" data-bs-toggle="modal" data-bs-target="#quickActionsModal">
                <div class="bg-secondary bg-gradient mx-auto mb-2 shadow-sm d-flex align-items-center justify-content-center rounded-3" style="width: 56px; height: 56px;">
                    <i class="fas fa-plus fs-4 text-white"></i>
                </div>
                <span class="text-dark small text-truncate d-block fw-medium">New Item</span>
            </a>
        </div>
    </div>
</div>

<style>
.hover-lift:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.08) !important;
}
</style>
'''

content = content.replace('<div class="dashboard-container">', f'<div class="dashboard-container">\n{new_header}')

with open('templates/index.html', 'w') as f:
    f.write(content)
