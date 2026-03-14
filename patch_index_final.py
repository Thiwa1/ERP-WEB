with open('templates/index.html', 'r') as f:
    content = f.read()

# I see there are leftover trailing bits:
#                <div class="tile">
#                             <i class="fas fa-file-invoice-dollar"></i>
#                             <span>Custom<br>Bal Sheet</span>
#                         </div>
#                     </a>
#                 </div>
#                <div class="tile">
#                             <i class="fas fa-balance-scale"></i>
#                             <span>Balance<br>Sheet</span>
#                         </div>
#                     </a>
#                 </div>

bad_tail = """               <div class="tile">
                            <i class="fas fa-file-invoice-dollar"></i>
                            <span>Custom<br>Bal Sheet</span>
                        </div>
                    </a>
                </div>
               <div class="tile">
                            <i class="fas fa-balance-scale"></i>
                            <span>Balance<br>Sheet</span>
                        </div>
                    </a>
                </div>
"""

if bad_tail in content:
    content = content.replace(bad_tail, "")
    with open('templates/index.html', 'w') as f:
        f.write(content)
    print("Removed bad tail.")
else:
    print("Could not find bad tail exact match.")
