setInterval(()=>{

fetch("/tasks/live/")

.then(r=>r.json())

.then(data=>{

data.tasks.forEach(task=>{

const el = document.querySelector(`[data-task='${task.id}']`)

if(!el) return

if(el.parentElement.parentElement.dataset.status !== task.status){

const column = document.querySelector(`[data-status='${task.status}'] .dropzone`)

column.appendChild(el)

}

})

})

},10000)