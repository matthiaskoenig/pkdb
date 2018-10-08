<template>
    <div id="comments" v-if="comments">
        Comments
        <span v-for="item in comments" :key="item.pk">
            <user-avatar :user="comment.user"></user-avatar>
            {{ comment.text }}<br />
        </span>
    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Object,
            }
        }
    }
</script>

<style scoped>

</style>