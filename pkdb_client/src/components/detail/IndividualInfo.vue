<template>
    <div id="individual-info">
        <md-list class="md-double-line">
            <div class="md-list-item-text">
                <span>{{ individual.name }}</span>
                <span>Name</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ individual.study_name }}</span>
                <span>Study</span>
            </div>
            <div class="md-list-item-text">
                <span>{{ individual.group }}</span>
                <span>Group</span>
            </div>
        </md-list>
    </div>
</template>

<script>
    export default {
        name: "IndividualInfo",
        props: {
            individual: {
                type: Object,
                //required: true,
            }
        }
    }
</script>

<style scoped>

</style>