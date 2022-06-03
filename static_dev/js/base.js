// utility functions and inventory management for VISOR frontend

// convenience shorthand functions
const gid = function(element) {return document.getElementById(element)}
const gcn = function(className) {
    return document.getElementsByClassName(className)
}
const gen = function(name) {return document.getElementsByName(name)}
const gtn = function(tagName) {
    return document.getElementsByTagName(tagName)
}

const inventoryPKs = function() {
    return Array.from(gen("inventory-item"))
        .map(item => Number(item.value))
}

const resultsCheckboxes = function() {
    return Array.from(gen("results-selection"))
}

const resultsSelections = function() {
    return resultsCheckboxes()
        .filter(box => box.checked)
        .map(item => Number(item.value))
}

// Select all toggles
const toggle = function (source) {
    resultsCheckboxes().forEach(
        function (box) {box.checked = source.checked})
}

const inventoryToggle = function (source) {
    inventoryBoxes.forEach(
        function (box) {box.checked = source.checked}
    )
}

const checkFactory = function(value, idPrefix="") {
    return `<label for="${idPrefix}-check${value}">
        <input type="checkbox"
        name="${idPrefix}-selection"
        class="factory-checkbox"
        id="${idPrefix}-check${value}"
        value=${value}>
        <span></span>
        </label>`
}


const dropSelected = function() {
    Array.from(inventoryBoxes)
        .filter(box => box.checked)
        .map(box => gid(box.id.replace("-check", ""))
        .remove()
    )
    updateInventory()
    if (inventoryPKs().length === 0) {gid("inventory-select-all")
    }
}

const dropAll = function() {
    Array.from(inventoryBoxes).map(
        box => gid(box.id.replace("-check", "")).remove()
    )
    updateInventory()
}

const undefinedToNone = function(obj) {
    if (obj === undefined) {
        return "none"
    }
    return obj
}

const addTableRow = function(sample, tableClass, parentTable, fields) {
    let tableRow = `<tr class="${tableClass}-row"  
        id="${tableClass}${sample["id"]}">
        <td class="${tableClass}-check-data">
        ${checkFactory(sample["id"], tableClass)}</td>`
    let rowContent = fields.map(field => undefinedToNone(sample[field]))
    rowContent.forEach(function (field) {
        tableRow += `<td class="${tableClass}-column">${field}</td>`
    })
    tableRow += `<input type="hidden" name=${tableClass}-item `
    tableRow += `value="${sample["id"]}"></tr>`
    parentTable.innerHTML += tableRow
}

const pickUpSelected = function() {
    Array.from(resultsSelections()).forEach(function(id) {
        if (inventoryPKs().includes(id)) {
            return
        }
        let sample = samples.filter(item => item["id"] === id)[0]
        addTableRow(sample, 'inventory', inventory, ["sample_id", "sample_name"])
    })
    updateInventory()
}

const checkInventory = function () {
    const inventoryCall = new XMLHttpRequest()
    inventoryCall.open("GET", "/visor/inventory_check/")
    inventoryCall.responseType = "json"
    inventoryCall.onload = function () {
    if (inventoryCall.readyState === inventoryCall.DONE) {
            const inventoryJSON = inventoryCall.response
            populateInventoryDiv(inventoryJSON)
        }
    }
    inventoryCall.send()
}


const populateInventoryDiv = function(inventoryJSON) {
    inventoryJSON.forEach(
        sample => addTableRow(
            sample, 'inventory', inventory, ['sample_id', 'sample_name']
        )
    )
    gid("inventory-select-all-row")
        .style
        .display = inventoryBoxes.length === 0 ? "none" : "revert"
}

const updateInventory = function () {
    const inventoryCall = new XMLHttpRequest()
    const inventoryUrl = `/visor/inventory/?inventory=${JSON.stringify(inventoryPKs())}`
    inventoryCall.open("GET", inventoryUrl)
    inventoryCall.send()
    gid("inventory-select-all-row")
        .style
        .display = inventoryBoxes.length === 0 ? "none" : "revert"
    }

const loadListen = function (func) {
    document.addEventListener("DOMContentLoaded", func)
}




