<template>
    <div id="individual-info">
        Name: {{ individual.name }}<br />
        Group: {{ individual.group }}<br />
        Study: {{ individual.study_name }}<br />
    </div>
</template>

<script>
    export default {
        name: "IndividualInfo",
        props: {
            individual: {
                type: Object,
                required: true,
            }
        }
    }
</script>

<style scoped>

</style>