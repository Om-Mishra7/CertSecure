let csvFile = document.getElementById('csv-file');


csvFile.addEventListener('change', () => {

    let csvFile = document.getElementById('csv-file');

    let formData = new FormData();

    formData.append('csv-file', csvFile.files[0]);

    let queryParams = new URLSearchParams(window.location.search);
    formData.append('certificateID', queryParams.get('certificateID'));


    fetch('/api/v1/csv-to-json', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {

            if (data.status === 'error') {
                createAlert(data.message, 'danger');
                document.getElementById('csv-file').value = '';
                return;
            }

            let table = document.getElementById('csv-data');
            let columns = data.data.columns;
            let tableBodyData = data.data.data;

            // Clear existing table content
            table.innerHTML = '';

            // Create table header
            let tableHead = document.createElement('thead');
            let tableHeadRow = document.createElement('tr');

            for (let i = 0; i < columns.length; i++) {
                let tableHeadColumn = document.createElement('th');
                tableHeadColumn.innerHTML = columns[i];
                tableHeadRow.appendChild(tableHeadColumn);
            }

            tableHead.appendChild(tableHeadRow);
            table.appendChild(tableHead);

            // Create table body
            let tableBody = document.createElement('tbody');

            for (let i = 0; i < tableBodyData.length; i++) {
                // Skip empty rows
                if (tableBodyData[i].length === 0) {
                    continue;
                }

                let tableBodyRow = document.createElement('tr');

                for (let j = 0; j < tableBodyData[i].length; j++) {
                    let tableBodyColumn = document.createElement('td');
                    tableBodyColumn.innerHTML = tableBodyData[i][j];
                    tableBodyRow.appendChild(tableBodyColumn);
                }

                tableBody.appendChild(tableBodyRow);
            }

            table.appendChild(tableBody);

            document.getElementById('confirm-csv').style.display = 'flex';



        })
        .catch(error => {
            document.getElementById('csv-file').value = '';
            createAlert("Something went wrong. Please try again.", 'danger');
        }
        );
});

function confirmCSV() {

    let csvFile = document.getElementById('csv-file');

    let formData = new FormData();


    formData.append('csv-file', csvFile.files[0]);

    let queryParams = new URLSearchParams(window.location.search);
    formData.append('certificateID', queryParams.get('certificateID'));

    fetch('/api/v1/organization/create-certificates', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'error') {
                createAlert(data.message, 'danger');
                return;
            }

            createAlert(data.message, 'success');
            setTimeout(() => {
                window.location.href = '/organization/dashboard';
            }, 1000);
        })
        .catch(error => {
            createAlert("Something went wrong. Please try again.", 'danger');
        }
        );
}

