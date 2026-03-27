with open('templates/base.html', 'r') as f:
    content = f.read()

win10_modal = """<!-- Quick Actions Modal (Win10 Style) -->
    <style>
        .win10-modal-dialog { max-width: 850px; }
        .win10-modal-content {
            background: #202020; color: #ffffff; border: 1px solid #333;
            border-radius: 0; display: flex; flex-direction: row; height: 550px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .win10-sidebar { width: 48px; background: #181818; display: flex; flex-direction: column; align-items: center; padding-top: 10px; border-right: 1px solid #333; }
        .win10-sidebar-icon { color: #fff; padding: 15px 0; width: 100%; text-align: center; cursor: pointer; transition: background 0.2s; }
        .win10-sidebar-icon:hover { background: rgba(255, 255, 255, 0.1); }
        .win10-main-content { flex-grow: 1; padding: 20px 30px; display: flex; flex-direction: column; overflow-y: auto; }
        .win10-search-box { background: #fff; border-radius: 0; padding: 8px 15px; display: flex; align-items: center; margin-bottom: 25px; border: 2px solid transparent; border-bottom: 2px solid #0078D7; }
        .win10-search-box input { border: none; background: transparent; width: 100%; margin-left: 10px; outline: none; color: #000; }
        .win10-search-box i { color: #666; }
        .win10-layout { display: flex; gap: 30px; }
        .win10-groups { flex: 2; display: flex; flex-direction: column; gap: 25px; }
        .win10-recents { flex: 1; border-left: 1px solid #333; padding-left: 20px; }
        .win10-category-title { font-size: 14px; font-weight: 500; margin-bottom: 12px; color: #fff; letter-spacing: 0.5px; }
        .win10-tile-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
        .win10-tile { background: #0078D7; color: #fff; text-decoration: none; padding: 15px; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: transform 0.1s, filter 0.2s; height: 100px; cursor: pointer; border: 2px solid transparent; position: relative; }
        .win10-tile:hover { filter: brightness(1.2); border-color: rgba(255,255,255,0.3); color: #fff; }
        .win10-tile:active { transform: scale(0.96); }
        .win10-tile i { font-size: 28px; margin-bottom: 10px; }
        .win10-tile span { font-size: 12px; text-align: center; line-height: 1.2; }
        .tile-blue { background: #0078D7; } .tile-green { background: #107C10; } .tile-orange { background: #D83B01; } .tile-purple { background: #5C2D91; } .tile-teal { background: #008272; } .tile-red { background: #E81123; }
        .win10-recent-list { display: flex; flex-direction: column; gap: 5px; }
        .win10-recent-item { display: flex; align-items: center; padding: 10px 12px; color: #fff; text-decoration: none; transition: background 0.2s; border-radius: 4px; }
        .win10-recent-item:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }
        .win10-recent-item i { width: 30px; font-size: 16px; text-align: center; }
    </style>
    <div class="modal fade" id="quickActionsModal" tabindex="-1" aria-hidden="true" style="z-index: 1055;">
        <div class="modal-dialog modal-dialog-centered win10-modal-dialog">
            <div class="modal-content win10-modal-content">
                <div class="win10-sidebar">
                    <div class="win10-sidebar-icon" data-bs-dismiss="modal"><i class="fas fa-bars"></i></div>
                    <div style="flex-grow: 1;"></div>
                    <div class="win10-sidebar-icon"><i class="fas fa-user"></i></div>
                    <div class="win10-sidebar-icon"><i class="fas fa-cog"></i></div>
                    <div class="win10-sidebar-icon" data-bs-dismiss="modal"><i class="fas fa-power-off text-danger"></i></div>
                </div>
                <div class="win10-main-content">
                    <div class="win10-search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" id="win10SearchInput" placeholder="Type here to search apps, settings, and more" autofocus autocomplete="off">
                    </div>
                    <div class="win10-layout">
                        <div class="win10-groups" id="win10GridContainer">
                            <div class="win10-category">
                                <div class="win10-category-title">Company Setup</div>
                                <div class="win10-tile-grid">
                                    <a href="/company_profile" class="win10-tile tile-blue" data-name="company profile"><i class="fas fa-id-card"></i><span>Company</span></a>
                                    <a href="/create_bank_account" class="win10-tile tile-blue" data-name="bank account"><i class="fas fa-university"></i><span>Bank Acc</span></a>
                                    <a href="/admin/users" class="win10-tile tile-blue" data-name="users admin"><i class="fas fa-user-plus"></i><span>Users</span></a>
                                    <a href="/control_panel" class="win10-tile tile-blue" data-name="system control panel"><i class="fas fa-sliders-h"></i><span>System</span></a>
                                </div>
                            </div>
                            <div class="win10-category">
                                <div class="win10-category-title">Suppliers & Customers</div>
                                <div class="win10-tile-grid">
                                    <a href="/add_customer" class="win10-tile tile-green" data-name="add new customer"><i class="fas fa-user-tag"></i><span>Customer</span></a>
                                    <a href="/add_supplier" class="win10-tile tile-green" data-name="add new supplier"><i class="fas fa-truck"></i><span>Supplier</span></a>
                                </div>
                            </div>
                            <div class="win10-category">
                                <div class="win10-category-title">Point of Sales</div>
                                <div class="win10-tile-grid">
                                    <a href="/pos_settings" class="win10-tile tile-orange" data-name="pos settings"><i class="fas fa-cogs"></i><span>POS Set</span></a>
                                    <a href="/warranty_period" class="win10-tile tile-orange" data-name="warranty period"><i class="fas fa-shield-alt"></i><span>Warranty</span></a>
                                </div>
                            </div>
                            <div class="win10-category">
                                <div class="win10-category-title">Accounting</div>
                                <div class="win10-tile-grid">
                                    <a href="/balance_sheet_category" class="win10-tile tile-purple" data-name="balance sheet category"><i class="fas fa-balance-scale"></i><span>Bal Sheet</span></a>
                                    <a href="/pl_category" class="win10-tile tile-purple" data-name="profit loss category"><i class="fas fa-chart-pie"></i><span>P&L Cat</span></a>
                                    <a href="/add_new_account" class="win10-tile tile-purple" data-name="add new account"><i class="fas fa-file-invoice"></i><span>New Acc</span></a>
                                    <a href="/bulk_upload_gl" class="win10-tile tile-purple" data-name="bulk upload gl"><i class="fas fa-file-upload"></i><span>Bulk GL</span></a>
                                </div>
                            </div>
                            <div class="win10-category">
                                <div class="win10-category-title">Inventory Management</div>
                                <div class="win10-tile-grid">
                                    <a href="/inventory_locations" class="win10-tile tile-teal" data-name="inventory locations house"><i class="fas fa-warehouse"></i><span>Inv House</span></a>
                                    <a href="/add_inventory_item" class="win10-tile tile-teal" data-name="add inventory item"><i class="fas fa-box"></i><span>Inv Item</span></a>
                                </div>
                            </div>
                            <div class="win10-category">
                                <div class="win10-category-title">Other Tools</div>
                                <div class="win10-tile-grid">
                                    <a href="/tax_settings" class="win10-tile tile-teal" data-name="tax settings"><i class="fas fa-percent"></i><span>Tax</span></a>
                                    <a href="/system_backup" class="win10-tile tile-red" data-name="system backup download"><i class="fas fa-download"></i><span>Backup</span></a>
                                </div>
                            </div>
                        </div>
                        <div class="win10-recents win10-category" id="win10RecentCategory">
                            <div class="win10-category-title">Recent Actions</div>
                            <div class="win10-recent-list">
                                <a href="/add_customer" class="win10-recent-item" data-name="add customer"><i class="fas fa-user-plus text-primary"></i><div><div class="fw-bold" style="font-size: 14px;">Add Customer</div><div class="text-white-50" style="font-size: 12px;">Recently used</div></div></a>
                                <a href="/create_bank_account" class="win10-recent-item" data-name="create bank account"><i class="fas fa-university text-success"></i><div><div class="fw-bold" style="font-size: 14px;">Create Bank Account</div><div class="text-white-50" style="font-size: 12px;">Recently used</div></div></a>
                                <a href="/balance_sheet_category" class="win10-recent-item" data-name="balance sheet category"><i class="fas fa-balance-scale text-warning"></i><div><div class="fw-bold" style="font-size: 14px;">Balance Sheet Category</div><div class="text-white-50" style="font-size: 12px;">Recently used</div></div></a>
                                <a href="/journal_entry" class="win10-recent-item" data-name="journal entry"><i class="fas fa-book text-info"></i><div><div class="fw-bold" style="font-size: 14px;">Journal Entry</div><div class="text-white-50" style="font-size: 12px;">Used 5m ago</div></div></a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
"""

modal_start = content.find('<!-- Quick Actions Modal -->')

if modal_start != -1:
    scripts_start = content.find('<script>', modal_start)
    if scripts_start == -1:
        scripts_start = content.find('<script', modal_start)

    if scripts_start != -1:
        content = content[:modal_start] + win10_modal + "\n\n    " + content[scripts_start:]
        with open('templates/base.html', 'w') as f:
            f.write(content)
        print("Patched modal.")
else:
    print("Could not find start modal.")
