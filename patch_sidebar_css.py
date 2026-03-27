import re

with open("templates/base.html", "r") as f:
    content = f.read()

css_to_add = """
        /* Windows 11 Collapsed Sidebar Mode */
        body.sidebar-collapsed {
            --sidebar-width: 72px;
        }

        body.sidebar-collapsed .sidebar-brand {
            justify-content: center;
        }

        body.sidebar-collapsed .sidebar-brand .nav-text {
            display: none;
        }

        body.sidebar-collapsed .menu-category {
            display: none;
        }

        body.sidebar-collapsed .nav-link {
            justify-content: center;
            padding: 12px 0;
            margin-bottom: 8px;
            border-radius: 8px;
            margin-left: 8px;
            margin-right: 8px;
        }

        body.sidebar-collapsed .nav-link.active {
            padding-left: 0;
            border-radius: 8px;
            border-left: none;
            position: relative;
        }

        body.sidebar-collapsed .nav-link.active::before {
            content: '';
            position: absolute;
            left: -8px;
            top: 50%;
            transform: translateY(-50%);
            height: 16px;
            width: 3px;
            background-color: var(--accent-color);
            border-radius: 4px;
        }

        body.sidebar-collapsed .nav-link i {
            margin-right: 0;
            font-size: 1.3rem;
            text-align: center;
        }

        body.sidebar-collapsed .nav-link .nav-text {
            display: none;
        }

        body.sidebar-collapsed .btn-add-new-pro {
            padding: 12px 0;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            margin: 20px auto;
        }

        body.sidebar-collapsed .btn-add-new-pro .nav-text {
            display: none;
        }

        /* Win11 Sidebar Toggle Button */
        .sidebar-collapse-btn {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.7);
            border-radius: 50%;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            position: absolute;
            right: 12px;
            top: 24px;
            z-index: 1010;
        }
        .sidebar-collapse-btn:hover {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }

        body.sidebar-collapsed .sidebar-collapse-btn {
            right: 50%;
            transform: translateX(50%);
            top: 70px; /* Below the brand icon */
        }
        body.sidebar-collapsed .sidebar-collapse-btn i {
            transform: scaleX(-1); /* Flip the chevron */
        }

        @media (max-width: 991.98px) {
            body.sidebar-collapsed {
                --sidebar-width: 260px; /* Disable collapse on mobile, standard toggle takes over */
            }
            .sidebar-collapse-btn {
                display: none;
            }
        }
"""

content = content.replace("/* Main Content */", css_to_add + "\n        /* Main Content */")

with open("templates/base.html", "w") as f:
    f.write(content)
