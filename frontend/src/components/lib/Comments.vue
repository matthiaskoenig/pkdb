<template>
    <div id="comments" v-if="comments && comments.length>0">
        <span v-for="comment in comments">
            <user-avatar :user="comment.user" :comment="comment.text"/>
        </span>

    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Array,
                required:true,
            }
        }
    }
</script>

<style scoped>

</style>