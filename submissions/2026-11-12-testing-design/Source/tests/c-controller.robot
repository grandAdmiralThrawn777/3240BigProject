*** Settings ***
Suite Setup       Setup
Suite Teardown    Teardown
Test Teardown     Test Teardown
Resource          ${RENODEKEYWORDS}

*** Test Cases ***
C Firmware Boots And Drives Valve Output For Low Fixture
    Execute Command    include "${CURDIR}/../emulation/c-controller.resc"
    Create Terminal Tester    sysbus.usart2
    Start Emulation
    Wait For Line On Uart    C_RENODE_SETUP_OK    timeout=5
    Wait For Line On Uart    C_CONTROL_LOW_OPEN_OK    timeout=5
    ${output}=    Execute Command    sysbus ReadDoubleWord 0x40020C14
    Should Contain    ${output}    00001000
