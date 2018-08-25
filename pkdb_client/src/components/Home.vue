<template>
    <div>
        <h1>Pharmacokinetics Database</h1>
        <ul>
            <li>Studies: {{ studies_count }}</li>
            <li>Groups: {{ groups_count }}</li>
            <li>Individuals: {{ individuals_count }}</li>
            <li>Interventions: {{ interventions_count }}</li>
            <li>Outputs: {{ outputs_count }}</li>
            <li>Timecourses: {{ timecourses_count }}</li>
        </ul>
    </div>
</template>

<script>
    export default {
        name: 'Home'
    }
</script>
<style>
</style>