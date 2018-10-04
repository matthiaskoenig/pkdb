<template>
    <div>
        <h1>About</h1>
        <AboutInformation/>

        <h1>Statistics</h1>
        <Statistics/>
    </div>
</template>

<script>
    import Statistics from '@/components/statistics/Statistics'
    import AboutInformation from "./AboutInformation";

    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics
        },
    }
</script>

<style scoped></style>
