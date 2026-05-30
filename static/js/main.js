const inputs = document.querySelectorAll(".input");

function addcl(){
    let parent = this.parentNode.parentNode;
    parent.classList.add("focus");
}

function remcl(){
    let parent = this.parentNode.parentNode;
    if(this.value == ""){
        parent.classList.remove("focus");
    }
}

inputs.forEach(input => {
    input.addEventListener("focus", addcl);
    input.addEventListener("blur", remcl);
});

function loadSectionOptions(carreraSelect) {
    const form = carreraSelect.closest('form');
    if (!form) {
        return;
    }
    const sectionSelect = form.querySelector('select[name="seccion"]');
    if (!sectionSelect) {
        return;
    }

    const selectedValue = sectionSelect.dataset.selected || "";
    sectionSelect.innerHTML = '<option value="">Seleccione...</option>';
    const carrera = carreraSelect.value;
    if (!carrera) {
        return;
    }
    const sedeSelect = form.querySelector('select[name="id_sede"]');
    const sedeParam = sedeSelect ? `&sede=${encodeURIComponent(sedeSelect.value)}` : '';

    fetch(`/api/secciones?carrera=${encodeURIComponent(carrera)}${sedeParam}`)
        .then(response => response.json())
        .then(data => {
            if (!data.options) {
                return;
            }
            data.options.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option;
                opt.textContent = option;
                if (option === selectedValue) {
                    opt.selected = true;
                }
                sectionSelect.appendChild(opt);
            });
        })
        .catch(error => console.error('Error cargando secciones:', error));
}

function loadCourseOptions(form) {
    const sedeSelect = form.querySelector('select[name="id_sede"]');
    const carreraSelect = form.querySelector('select[name="carrera"]');
    const courseSelect = form.querySelector('select[name="id_curso"]');
    if (!sedeSelect || !carreraSelect || !courseSelect) {
        return;
    }

    const selectedValue = courseSelect.dataset.selected || "";
    courseSelect.innerHTML = '<option value="">Seleccione un curso...</option>';
    const idSede = sedeSelect.value;
    const carrera = carreraSelect.value;
    if (!idSede || !carrera) {
        return;
    }

    fetch(`/api/cursos?sede=${encodeURIComponent(idSede)}&carrera=${encodeURIComponent(carrera)}`)
        .then(response => response.json())
        .then(data => {
            if (!data.options) {
                return;
            }
            data.options.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option.id;
                opt.textContent = option.nombre;
                if (option.id.toString() === selectedValue) {
                    opt.selected = true;
                }
                courseSelect.appendChild(opt);
            });
        })
        .catch(error => console.error('Error cargando cursos:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    const careerSelects = document.querySelectorAll('select[name="carrera"]');
    careerSelects.forEach(select => {
        select.addEventListener('change', () => {
            loadSectionOptions(select);
            const form = select.closest('form');
            if (form) {
                loadCourseOptions(form);
            }
        });
        if (select.value) {
            loadSectionOptions(select);
            const form = select.closest('form');
            if (form) {
                loadCourseOptions(form);
            }
        }
    });
    // load carreras when sede changes (per-form)
    const sedeSelects = Array.from(document.querySelectorAll('select[name="sede"]'))
        .concat(Array.from(document.querySelectorAll('select[name="id_sede"]')));
    sedeSelects.forEach(sede => {
        sede.addEventListener('change', () => {
            const form = sede.closest('form');
            if (!form) return;
            const carreraSelect = form.querySelector('select[name="carrera"]');
            if (!carreraSelect) return;
            const selectedCareer = carreraSelect.value;
            carreraSelect.innerHTML = '<option value="">Seleccione...</option>';
            loadCourseOptions(form);
            const idSede = sede.value;
            if (!idSede) return;
            fetch(`/api/carreras?sede=${encodeURIComponent(idSede)}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.options) return;
                    data.options.forEach(option => {
                        const opt = document.createElement('option');
                        opt.value = option;
                        opt.textContent = option;
                        carreraSelect.appendChild(opt);
                    });
                    if (selectedCareer) {
                        carreraSelect.value = selectedCareer;
                    }
                    // if there's a valid selected value, try to trigger section and course load
                    if (carreraSelect.value) {
                        loadSectionOptions(carreraSelect);
                        loadCourseOptions(form);
                    }
                })
                .catch(e => console.error('Error cargando carreras:', e));
        });
        // if there is a preselected sede on load, trigger change to populate carreras
        if (sede.value) {
            sede.dispatchEvent(new Event('change'));
        }
    });
});